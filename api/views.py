from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum
from .models import Worker, Owner, Assignment, Payment, OwnerPayment
from .serializers import WorkerSerializer, OwnerSerializer, AssignmentSerializer, PaymentSerializer, OwnerPaymentSerializer
from django.utils import timezone

class WorkerViewSet(viewsets.ModelViewSet):
    serializer_class = WorkerSerializer

    def get_queryset(self):
        return Worker.objects.filter(is_deleted=False)

    def _auto_reset_workers(self):
        """After 4 AM IST each day, reset workers whose leave was set on a previous date."""
        now_ist = timezone.localtime(timezone.now())
        today_ist = now_ist.date()
        if now_ist.hour >= 4:
            Worker.objects.filter(
                is_active=False,
                is_deleted=False,
                leave_date__lt=today_ist
            ).update(is_active=True, status='AVAILABLE', leave_date=None)

    def list(self, request, *args, **kwargs):
        self._auto_reset_workers()
        return super().list(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        worker = self.get_object()
        worker.is_deleted = True
        worker.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Toggle worker active/leave status."""
        worker = self.get_object()
        worker.is_active = not worker.is_active
        # If going on leave, record today's IST date and mark UNAVAILABLE.
        # If coming back, clear leave_date and mark AVAILABLE.
        if not worker.is_active:
            worker.status = 'UNAVAILABLE'
            worker.leave_date = timezone.localdate()
        else:
            worker.status = 'AVAILABLE'
            worker.leave_date = None
        worker.save()
        return Response({'id': worker.id, 'is_active': worker.is_active})

class OwnerViewSet(viewsets.ModelViewSet):
    serializer_class = OwnerSerializer

    def get_queryset(self):
        return Owner.objects.filter(is_deleted=False)

    def destroy(self, request, *args, **kwargs):
        owner = self.get_object()
        owner.is_deleted = True
        owner.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def details(self, request, pk=None):
        owner = self.get_object()
        date_filter = request.query_params.get('date', None)

        all_assignments = Assignment.objects.filter(owner=owner)
        display_assignments = all_assignments.filter(date=date_filter) if date_filter else all_assignments

        serializer = AssignmentSerializer(display_assignments, many=True)

        # Totals are always all-time — owner pays in bulk regardless of date
        total_work_amount = all_assignments.aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid = OwnerPayment.objects.filter(owner=owner).aggregate(Sum('amount'))['amount__sum'] or 0
        total_pending = max(0, float(total_work_amount) - float(total_paid))

        payment_history = OwnerPayment.objects.filter(owner=owner).order_by('-date', '-id')

        return Response({
            'owner': OwnerSerializer(owner).data,
            'assignments': serializer.data,
            'totals': {
                'total_work_amount': total_work_amount,
                'total_paid': total_paid,
                'total_pending': total_pending
            },
            'payment_history': OwnerPaymentSerializer(payment_history, many=True).data
        })

    @action(detail=True, methods=['post'])
    def collect_payment(self, request, pk=None):
        """Record an owner-level payment of any amount."""
        owner = self.get_object()
        amount = request.data.get('amount')
        note = request.data.get('note', '')
        if not amount:
            return Response({'error': 'Amount is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            payment = OwnerPayment.objects.create(owner=owner, amount=float(amount), note=note)
            return Response(OwnerPaymentSerializer(payment).data, status=status.HTTP_201_CREATED)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid amount.'}, status=status.HTTP_400_BAD_REQUEST)

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

        collected_amount = OwnerPayment.objects.filter(
            date=date_str).aggregate(Sum('amount'))['amount__sum'] or 0
        pending_amount = max(0, float(total_earnings) - float(collected_amount))

        owners = Owner.objects.filter(is_deleted=False)
        owner_summary = []
        for owner in owners:
            oa = assignments.filter(owner=owner)
            if oa.exists():
                work_amt = oa.aggregate(Sum('amount'))['amount__sum'] or 0
                paid_amt = OwnerPayment.objects.filter(
                    owner=owner, date=date_str
                ).aggregate(Sum('amount'))['amount__sum'] or 0
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
