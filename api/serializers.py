from rest_framework import serializers
from .models import Worker, Owner, Assignment, Payment
from django.utils import timezone

class WorkerSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()

    class Meta:
        model = Worker
        fields = '__all__'

    def get_status(self, obj):
        # If worker is explicitly deactivated (on leave), status is UNAVAILABLE
        if not obj.is_active:
            return 'UNAVAILABLE'
        
        # Check if worker has any active assignment for TODAY
        today = timezone.now().date()
        has_active_assignment = obj.assignments.filter(date=today, is_active=True).exists()
        
        if has_active_assignment:
            return 'ASSIGNED'
        
        # Default status for any active worker at the start of the day
        return 'AVAILABLE'

class OwnerSerializer(serializers.ModelSerializer):
    assigned_workers_count = serializers.SerializerMethodField()
    total_work_amount = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()
    total_pending = serializers.SerializerMethodField()

    class Meta:
        model = Owner
        fields = ['id', 'name', 'phone', 'address', 'assigned_workers_count', 'total_work_amount', 'total_paid', 'total_pending']

    def get_assigned_workers_count(self, obj):
        # Only count active assignments for TODAY
        today = timezone.now().date()
        return obj.assignments.filter(date=today, is_active=True).count()

    def get_total_work_amount(self, obj):
        from django.db.models import Sum
        return obj.assignments.aggregate(Sum('amount'))['amount__sum'] or 0

    def get_total_paid(self, obj):
        from django.db.models import Sum
        return Payment.objects.filter(assignment__owner=obj).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0

    def get_total_pending(self, obj):
        work = float(self.get_total_work_amount(obj))
        paid = float(self.get_total_paid(obj))
        return max(0, work - paid)

class AssignmentSerializer(serializers.ModelSerializer):
    worker_name = serializers.ReadOnlyField(source='worker.name')
    owner_name = serializers.ReadOnlyField(source='owner.name')

    class Meta:
        model = Assignment
        fields = '__all__'

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
