from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import (
    Department, 
    UserProfile, 
    Printer, 
    UserPrinterAssignment,
    PricingConfig, 
    UserPricingProfile, 
    PrintJob, 
    SystemLog
)

# ====================
# INLINE ADMIN FOR USERPROFILE
# ====================

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Perfil'
    fk_name = 'user'

# ====================
# CUSTOM USER ADMIN
# ====================

class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    
    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(UserAdmin, self).get_inline_instances(request, obj)

# ====================
# MODEL ADMINS
# ====================

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'department_type', 'active', 'created_at')
    list_filter = ('department_type', 'active')
    search_fields = ('code', 'name')
    list_per_page = 20
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('code', 'name', 'department_type')
        }),
        ('Descripción', {
            'fields': ('description', 'active'),
            'classes': ('collapse',)
        }),
    )

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('get_username', 'get_full_name', 'role', 'department', 'is_verified', 'created_at')
    list_filter = ('role', 'is_verified', 'department')
    search_fields = ('user__username', 'user__email', 'student_id', 'user__first_name', 'user__last_name')
    list_per_page = 20
    
    fieldsets = (
        ('Usuario', {
            'fields': ('user', 'role')
        }),
        ('Información Académica', {
            'fields': ('department', 'student_id')
        }),
        ('Información de Contacto', {
            'fields': ('phone', 'address')
        }),
        ('Configuración', {
            'fields': ('is_verified', 'max_concurrent_jobs')
        }),
    )
    
    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Usuario'
    
    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'Nombre Completo'

@admin.register(Printer)
class PrinterAdmin(admin.ModelAdmin):
    list_display = ('name', 'serial_number', 'printer_type', 'status', 'location', 'is_active')
    list_filter = ('printer_type', 'status', 'is_active', 'department')
    search_fields = ('name', 'serial_number', 'brand', 'model', 'location')
    list_per_page = 20
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('serial_number', 'name', 'brand', 'model', 'printer_type')
        }),
        ('Estado y Ubicación', {
            'fields': ('status', 'location', 'department', 'is_active')
        }),
        ('Capacidades Técnicas', {
            'fields': ('build_volume_x', 'build_volume_y', 'build_volume_z', 
                      'max_temperature', 'supported_materials')
        }),
        ('Mantenimiento y Costos', {
            'fields': ('purchase_date', 'warranty_expiry', 'hourly_cost',
                      'maintenance_interval_hours', 'total_print_hours')
        }),
        ('Notas', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('total_print_hours',)

@admin.register(UserPrinterAssignment)
class UserPrinterAssignmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'printer', 'active', 'start_date', 'end_date', 'created_by')
    list_filter = ('active', 'start_date')
    search_fields = ('user__username', 'printer__name', 'reason')
    list_per_page = 20
    
    fieldsets = (
        ('Asignación', {
            'fields': ('user', 'printer', 'active')
        }),
        ('Período', {
            'fields': ('start_date', 'end_date')
        }),
        ('Información Adicional', {
            'fields': ('reason', 'created_by')
        }),
    )

@admin.register(PricingConfig)
class PricingConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'active', 'cost_per_hour', 'cost_per_gram', 'valid_from', 'is_currently_valid')
    list_filter = ('active', 'valid_from')
    search_fields = ('name',)
    list_per_page = 20
    
    fieldsets = (
        ('Información General', {
            'fields': ('name', 'active')
        }),
        ('Precios Base', {
            'fields': ('cost_per_hour', 'cost_per_gram', 'min_billing_hours')
        }),
        ('Multiplicadores por Material', {
            'fields': ('pla_multiplier', 'abs_multiplier', 'petg_multiplier', 'resin_multiplier')
        }),
        ('Descuentos por Rol', {
            'fields': ('student_discount', 'teacher_discount')
        }),
        ('Período de Validez', {
            'fields': ('valid_from', 'valid_to')
        }),
        ('Comisiones', {
            'fields': ('commission_percentage',),
            'classes': ('collapse',)
        }),
    )
    
    def is_currently_valid(self, obj):
        return obj.is_currently_valid
    is_currently_valid.boolean = True
    is_currently_valid.short_description = 'Válido Actualmente'

@admin.register(UserPricingProfile)
class UserPricingProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'credit_limit', 'available_credit', 'total_spent')
    search_fields = ('user__username', 'user__email')
    list_per_page = 20
    
    fieldsets = (
        ('Usuario', {
            'fields': ('user', 'pricing_config')
        }),
        ('Saldo y Límites', {
            'fields': ('balance', 'credit_limit', 'discount_percentage')
        }),
        ('Historial', {
            'fields': ('total_spent', 'last_payment_date'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('total_spent', 'last_payment_date')
    
    def available_credit(self, obj):
        return obj.available_credit
    available_credit.short_description = 'Crédito Disponible'

@admin.register(PrintJob)
class PrintJobAdmin(admin.ModelAdmin):
    list_display = ('job_id_short', 'user', 'printer', 'status', 'material_type', 'created_at', 'estimated_cost')
    list_filter = ('status', 'material_type', 'created_at')
    search_fields = ('job_id', 'user__username', 'file_name')
    list_per_page = 20
    
    fieldsets = (
        ('Identificación', {
            'fields': ('job_id', 'user', 'printer')
        }),
        ('Archivo y Material', {
            'fields': ('file_name', 'file_size', 'material_type', 'material_weight')
        }),
        ('Tiempos y Estado', {
            'fields': ('estimated_hours', 'actual_hours', 'status', 'priority')
        }),
        ('Configuración de Impresión', {
            'fields': ('layer_height', 'infill_percentage', 'supports'),
            'classes': ('collapse',)
        }),
        ('Aprobación', {
            'fields': ('approved_by', 'approved_at')
        }),
        ('Tiempos de Ejecución', {
            'fields': ('started_at', 'completed_at', 'cancelled_at'),
            'classes': ('collapse',)
        }),
        ('Costos y Pago', {
            'fields': ('estimated_cost', 'actual_cost', 'paid')
        }),
        ('Notas y Errores', {
            'fields': ('notes', 'error_message'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('job_id', 'created_at', 'updated_at')
    
    def job_id_short(self, obj):
        return str(obj.job_id)[:8] + "..."
    job_id_short.short_description = 'ID Trabajo'

@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = ('log_id_short', 'user', 'action', 'model_name', 'object_id', 'created_at')
    list_filter = ('action', 'model_name', 'created_at')
    search_fields = ('user__username', 'description', 'object_id')
    list_per_page = 30
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('log_id', 'user', 'action', 'model_name', 'object_id')
        }),
        ('Descripción', {
            'fields': ('description',)
        }),
        ('Datos de Auditoría', {
            'fields': ('before_data', 'after_data'),
            'classes': ('collapse',)
        }),
        ('Información Técnica', {
            'fields': ('ip_address', 'user_agent', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('log_id', 'created_at', 'ip_address', 'user_agent')
    
    def log_id_short(self, obj):
        return str(obj.log_id)[:8] + "..."
    log_id_short.short_description = 'ID Log'



# Desregistrar el User admin por defecto
admin.site.unregister(User)
# Registrar con nuestro UserAdmin personalizado
admin.site.register(User, UserAdmin)

# Los demás modelos ya están registrados con los decoradores @admin.register
