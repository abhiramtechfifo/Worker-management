from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum
from .models import Worker, Owner, Assignment, Payment
from .serializers import WorkerSerializer, OwnerSerializer, AssignmentSerializer, PaymentSerializer
from django.utils import timezone

class WorkerViewSet(viewsets.ModelViewSet):
    queryset = Worker.objects.all()
    serializer_class = WorkerSerializer

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Toggle worker active/leave status."""
        worker = self.get_object()
        worker.is_active = not worker.is_active
        # If going on leave, status is UNAVAILABLE. If coming back, status is AVAILABLE.
        if not worker.is_active:
            worker.status = 'UNAVAILABLE'
        else:
            worker.status = 'AVAILABLE'
        worker.save()
        return Response({'id': worker.id, 'is_active': worker.is_active})

class OwnerViewSet(viewsets.ModelViewSet):
    queryset = Owner.objects.all()
    serializer_class = OwnerSerializer

    @action(detail=True, methods=['get'])
    def details(self, request, pk=None):
        owner = self.get_object()
        date_filter = request.query_params.get('date', None)

        assignments = Assignment.objects.filter(owner=owner)
        if date_filter:
            assignments = assignments.filter(date=date_filter)

        serializer = AssignmentSerializer(assignments, many=True)

        total_work_amount = assignments.aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid = Payment.objects.filter(assignment__in=assignments).aggregate(
            Sum('amount_paid'))['amount_paid__sum'] or 0
        total_pending = max(0, float(total_work_amount) - float(total_paid))

        return Response({
            'owner': OwnerSerializer(owner).data,
            'assignments': serializer.data,
            'totals': {
                'total_work_amount': total_work_amount,
                'total_paid': total_paid,
                'total_pending': total_pending
            }
        })

class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all().order_by('-date', '-id')
    serializer_class = AssignmentSerializer

    def perform_create(self, serializer):
        assignment = serializer.save()
        worker = assignment.worker
        worker.status = 'ASSIGNED'
        worker.save()

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Toggle assignment active/inactive (for nightly reset)."""
        assignment = self.get_object()
        assignment.is_active = not assignment.is_active
        assignment.save()
        # If deactivating, free up the worker
        if not assignment.is_active:
            worker = assignment.worker
            # Only reset if no other active assignments today
            other = Assignment.objects.filter(
                worker=worker, is_active=True
            ).exclude(id=assignment.id).exists()
            if not other:
                worker.status = 'AVAILABLE'
                worker.save()
        return Response({'id': assignment.id, 'is_active': assignment.is_active})

    @action(detail=True, methods=['delete'])
    def remove(self, request, pk=None):
        """Delete assignment and free up the worker."""
        assignment = self.get_object()
        worker = assignment.worker
        assignment.delete()
        # Free worker if no other active assignments remain
        other = Assignment.objects.filter(worker=worker, is_active=True).exists()
        if not other:
            worker.status = 'AVAILABLE'
            worker.save()
        return Response({'detail': 'Assignment removed.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'])
    def update_amount(self, request, pk=None):
        """Update the amount for an assignment."""
        assignment = self.get_object()
        amount = request.data.get('amount')
        if amount is None:
            return Response({'error': 'Amount is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            assignment.amount = float(amount)
            assignment.save()
        except (ValueError, TypeError):
            return Response({'error': 'Invalid amount.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AssignmentSerializer(assignment).data)

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        assignment_id = request.data.get('assignment')
        if assignment_id:
            try:
                assignment = Assignment.objects.get(id=assignment_id)
                total_paid = Payment.objects.filter(assignment=assignment).aggregate(
                    Sum('amount_paid'))['amount_paid__sum'] or 0
                if float(total_paid) >= float(assignment.amount):
                    assignment.status = 'Full Payment'
                elif float(total_paid) > 0:
                    assignment.status = 'Half Payment'
                else:
                    assignment.status = 'Pending'
                assignment.save()
            except Assignment.DoesNotExist:
                pass
        return response

class ReportViewSet(viewsets.ViewSet):
    def list(self, request):
        date_str = request.query_params.get('date', timezone.now().date().isoformat())
        assignments = Assignment.objects.filter(date=date_str)

        total_works = assignments.count()
        kooli_works = assignments.filter(work_type='KOOLI').count()
        grass_cutter_works = assignments.filter(work_type='GRASS_CUTTER').count()
        total_earnings = assignments.aggregate(Sum('amount'))['amount__sum'] or 0

        collected_amount = Payment.objects.filter(
            assignment__date=date_str).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
        pending_amount = max(0, float(total_earnings) - float(collected_amount))

        owners = Owner.objects.all()
        owner_summary = []
        for owner in owners:
            oa = assignments.filter(owner=owner)
            if oa.exists():
                work_amt = oa.aggregate(Sum('amount'))['amount__sum'] or 0
                paid_amt = Payment.objects.filter(
                    assignment__owner=owner, assignment__date=date_str
                ).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
                owner_summary.append({
                    'owner_name': owner.name,
                    'worker_count': oa.count(),
                    'total_work_amount': work_amt,
                    'paid_amount': paid_amt,
                    'pending_amount': max(0, float(work_amt) - float(paid_amt))
                })

        return Response({
            'summary': {
                'total_works': total_works,
                'kooli_works': kooli_works,
                'grass_cutter_works': grass_cutter_works,
                'total_earnings': total_earnings,
                'collected_amount': collected_amount,
                'pending_amount': pending_amount
            },
            'owner_summary': owner_summary
        })
