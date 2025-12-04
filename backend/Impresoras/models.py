# printers/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
from django.utils import timezone

class DepartmentType(models.TextChoices):
    ENGINEERING = 'ENG', 'Ingeniería'
    DESIGN = 'DES', 'Diseño'
    ARCHITECTURE = 'ARC', 'Arquitectura'
    ART = 'ART', 'Arte'
    SCIENCE = 'SCI', 'Ciencias'
    TECHNOLOGY = 'TEC', 'Tecnología'
    OTHER = 'OTH', 'Otro'


class UserRole(models.TextChoices):
    STUDENT = 'STU', 'Estudiante'
    TEACHER = 'TEA', 'Profesor'
    TECHNICIAN = 'TEC', 'Técnico'
    ADMIN = 'ADM', 'Administrador'
    EXTERNAL = 'EXT', 'Externo'


class PrinterStatus(models.TextChoices):
    AVAILABLE = 'AVA', 'Disponible'
    PRINTING = 'PRI', 'Imprimiendo'
    MAINTENANCE = 'MAI', 'En Mantenimiento'
    RESERVED = 'RES', 'Reservada'
    OUT_OF_SERVICE = 'OUT', 'Fuera de Servicio'


class PrinterType(models.TextChoices):
    FDM = 'FDM', 'FDM/FFF (Filamento)'
    SLA = 'SLA', 'SLA (Resina)'
    SLS = 'SLS', 'SLS (Polvo)'
    DLP = 'DLP', 'DLP (Resina)'


class JobStatus(models.TextChoices):
    PENDING = 'PEN', 'Pendiente'
    APPROVED = 'APP', 'Aprobado'
    PRINTING = 'PRI', 'Imprimiendo'
    PAUSED = 'PAU', 'Pausado'
    COMPLETED = 'COM', 'Completado'
    CANCELLED = 'CAN', 'Cancelado'
    FAILED = 'FAI', 'Fallido'


class MaterialType(models.TextChoices):
    PLA = 'PLA', 'PLA'
    ABS = 'ABS', 'ABS'
    PETG = 'PET', 'PETG'
    TPU = 'TPU', 'TPU (Flexible)'
    RESIN = 'RES', 'Resina'
    NYLON = 'NYL', 'Nylon'
    OTHER = 'OTH', 'Otro'


class LogAction(models.TextChoices):
    CREATE = 'CRE', 'Creación'
    UPDATE = 'UPD', 'Actualización'
    DELETE = 'DEL', 'Eliminación'
    LOGIN = 'LOG', 'Inicio de Sesión'
    LOGOUT = 'OUT', 'Cierre de Sesión'
    PRINT_START = 'PST', 'Inicio de Impresión'
    PRINT_END = 'PEN', 'Fin de Impresión'
    PAYMENT = 'PAY', 'Pago'
    ERROR = 'ERR', 'Error'


# ====================
# MODEL DEFINITIONS
# ====================

class Department(models.Model):
    """Departamentos académicos de la escuela"""
    code = models.CharField(max_length=10, unique=True, verbose_name="Código")
    name = models.CharField(max_length=100, verbose_name="Nombre")
    department_type = models.CharField(
        max_length=3,
        choices=DepartmentType.choices,
        default=DepartmentType.OTHER,
        verbose_name="Tipo de Departamento"
    )
    description = models.TextField(blank=True, verbose_name="Descripción")
    active = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Departamento"
        verbose_name_plural = "Departamentos"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def active_users_count(self):
        """Número de usuarios activos en este departamento"""
        return self.userprofile_set.filter(user__is_active=True).count()
    
    @property
    def active_printers_count(self):
        """Número de impresoras activas asignadas a este departamento"""
        # Asumiendo que las impresoras tienen departamento o están asignadas a usuarios del departamento
        return Printer.objects.filter(
            userprinterassignment__user__userprofile__department=self,
            status__in=[PrinterStatus.AVAILABLE, PrinterStatus.PRINTING, PrinterStatus.RESERVED]
        ).distinct().count()


class UserProfile(models.Model):
    """Extensión del modelo User para roles y departamento"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name="Usuario"
    )
    role = models.CharField(
        max_length=3,
        choices=UserRole.choices,
        default=UserRole.STUDENT,
        verbose_name="Rol"
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_profiles',
        verbose_name="Departamento"
    )
    student_id = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Carné de Estudiante"
    )
    phone = models.CharField(max_length=15, blank=True, verbose_name="Teléfono")
    address = models.TextField(blank=True, verbose_name="Dirección")
    is_verified = models.BooleanField(default=False, verbose_name="Verificado")
    max_concurrent_jobs = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Máximo de Trabajos Concurrentes"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"
        ordering = ['user__last_name', 'user__first_name']
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.get_role_display()})"
    
    @property
    def full_name(self):
        return self.user.get_full_name()
    
    @property
    def email(self):
        return self.user.email
    
    @property
    def is_active_user(self):
        return self.user.is_active
    
    @property
    def can_print(self):
        """Verifica si el usuario puede imprimir"""
        return self.is_verified and self.user.is_active
    
    def save(self, *args, **kwargs):
        # Si es estudiante, asegurar que tenga carné
        if self.role == UserRole.STUDENT and not self.student_id:
            raise ValueError("Los estudiantes deben tener un carné de estudiante")
        super().save(*args, **kwargs)


class Printer(models.Model):
    """Modelo para impresoras 3D"""
    serial_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Número de Serie"
    )
    name = models.CharField(max_length=100, verbose_name="Nombre")
    brand = models.CharField(max_length=50, verbose_name="Marca")
    model = models.CharField(max_length=50, verbose_name="Modelo")
    printer_type = models.CharField(
        max_length=3,
        choices=PrinterType.choices,
        default=PrinterType.FDM,
        verbose_name="Tipo de Impresora"
    )
    status = models.CharField(
        max_length=3,
        choices=PrinterStatus.choices,
        default=PrinterStatus.AVAILABLE,
        verbose_name="Estado"
    )
    
    # Capacidades técnicas
    build_volume_x = models.FloatField(verbose_name="Volumen X (mm)")
    build_volume_y = models.FloatField(verbose_name="Volumen Y (mm)")
    build_volume_z = models.FloatField(verbose_name="Volumen Z (mm)")
    max_temperature = models.FloatField(
        verbose_name="Temperatura Máxima (°C)",
        null=True,
        blank=True
    )
    supported_materials = models.CharField(
        max_length=200,
        verbose_name="Materiales Soportados",
        help_text="Separados por comas"
    )
    
    # Ubicación y departamento
    location = models.CharField(max_length=100, verbose_name="Ubicación")
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='printers',
        verbose_name="Departamento Asociado"
    )
    
    # Información adicional
    purchase_date = models.DateField(verbose_name="Fecha de Compra")
    warranty_expiry = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fin de Garantía"
    )
    hourly_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Costo por Hora (CUP)"
    )
    maintenance_interval_hours = models.IntegerField(
        default=500,
        verbose_name="Intervalo de Mantenimiento (horas)"
    )
    total_print_hours = models.FloatField(
        default=0,
        verbose_name="Horas Totales de Impresión"
    )
    notes = models.TextField(blank=True, verbose_name="Notas")
    is_active = models.BooleanField(default=True, verbose_name="Activa")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Impresora"
        verbose_name_plural = "Impresoras"
        ordering = ['name', 'brand']
    
    def __str__(self):
        return f"{self.name} ({self.serial_number}) - {self.get_status_display()}"
    
    @property
    def build_volume(self):
        """Volumen de construcción en cm³"""
        return round((self.build_volume_x * self.build_volume_y * self.build_volume_z) / 1000, 2)
    
    @property
    def needs_maintenance(self):
        """Verifica si necesita mantenimiento"""
        return self.total_print_hours >= self.maintenance_interval_hours
    
    @property
    def current_assignment(self):
        """Asignación actual activa"""
        return self.userprinterassignment_set.filter(
            active=True,
            start_date__lte=timezone.now()
        ).first()
    
    @property
    def can_print(self):
        """Verifica si puede imprimir"""
        return (
            self.is_active and 
            self.status in [PrinterStatus.AVAILABLE, PrinterStatus.RESERVED]
        )
    
    def update_print_hours(self, hours):
        """Actualiza las horas totales de impresión"""
        self.total_print_hours += hours
        self.save(update_fields=['total_print_hours'])


class UserPrinterAssignment(models.Model):
    """Asignaciones de impresoras a usuarios"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='printer_assignments',
        verbose_name="Usuario"
    )
    printer = models.ForeignKey(
        Printer,
        on_delete=models.CASCADE,
        related_name='user_assignments',
        verbose_name="Impresora"
    )
    active = models.BooleanField(default=True, verbose_name="Activa")
    start_date = models.DateTimeField(default=timezone.now, verbose_name="Fecha Inicio")
    end_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha Fin"
    )
    reason = models.TextField(verbose_name="Razón de Asignación")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_assignments',
        verbose_name="Creado por"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Asignación Usuario-Impresora"
        verbose_name_plural = "Asignaciones Usuario-Impresora"
        ordering = ['-start_date']
        unique_together = ['user', 'printer', 'active']
    
    def __str__(self):
        return f"{self.user.username} - {self.printer.name} ({'Activa' if self.active else 'Inactiva'})"
    
    @property
    def duration_days(self):
        """Duración de la asignación en días"""
        if self.end_date:
            return (self.end_date - self.start_date).days
        return (timezone.now() - self.start_date).days
    
    def deactivate(self):
        """Desactiva la asignación"""
        self.active = False
        self.end_date = timezone.now()
        self.save()
    
    def is_active_assignment(self):
        """Verifica si la asignación está activa actualmente"""
        if not self.active:
            return False
        if self.end_date and timezone.now() > self.end_date:
            return False
        return True


class PricingConfig(models.Model):
    """Configuración de precios del sistema"""
    name = models.CharField(max_length=100, verbose_name="Nombre de la Configuración")
    active = models.BooleanField(default=True, verbose_name="Activa")
    
    # Precios base
    cost_per_hour = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Costo por Hora (CUP)"
    )
    cost_per_gram = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Costo por Gramo (CUP)"
    )
    
    # Multiplicadores por tipo de material
    pla_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.0,
        verbose_name="Multiplicador PLA"
    )
    abs_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.2,
        verbose_name="Multiplicador ABS"
    )
    petg_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.1,
        verbose_name="Multiplicador PETG"
    )
    resin_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=2.0,
        verbose_name="Multiplicador Resina"
    )
    
    # Descuentos por rol
    student_discount = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.2,
        verbose_name="Descuento Estudiantes (%)"
    )
    teacher_discount = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.1,
        verbose_name="Descuento Profesores (%)"
    )
    
    # Tiempo mínimo de facturación (horas)
    min_billing_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.5,
        verbose_name="Horas Mínimas de Facturación"
    )
    
    # Configuración de comisiones
    commission_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.0,
        verbose_name="Comisión (%)"
    )
    
    valid_from = models.DateTimeField(default=timezone.now, verbose_name="Válido Desde")
    valid_to = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Válido Hasta"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Configuración de Precios"
        verbose_name_plural = "Configuraciones de Precios"
        ordering = ['-valid_from']
    
    def __str__(self):
        return f"{self.name} ({'Activa' if self.active else 'Inactiva'})"
    
    @property
    def is_currently_valid(self):
        """Verifica si la configuración es válida actualmente"""
        now = timezone.now()
        if self.valid_to and now > self.valid_to:
            return False
        return now >= self.valid_from
    
    def get_material_multiplier(self, material_type):
        """Obtiene el multiplicador para un tipo de material"""
        multipliers = {
            MaterialType.PLA: self.pla_multiplier,
            MaterialType.ABS: self.abs_multiplier,
            MaterialType.PETG: self.petg_multiplier,
            MaterialType.RESIN: self.resin_multiplier,
        }
        return multipliers.get(material_type, 1.0)
    
    def get_role_discount(self, role):
        """Obtiene el descuento para un rol"""
        discounts = {
            UserRole.STUDENT: self.student_discount,
            UserRole.TEACHER: self.teacher_discount,
        }
        return discounts.get(role, 0.0)


class UserPricingProfile(models.Model):
    """Perfil de precios y saldo del usuario"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='pricing_profile',
        verbose_name="Usuario"
    )
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Saldo (CUP)"
    )
    credit_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=1000.00,
        verbose_name="Límite de Crédito (CUP)"
    )
    pricing_config = models.ForeignKey(
        PricingConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Configuración de Precios"
    )
    last_payment_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Última Fecha de Pago"
    )
    total_spent = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Total Gastado (CUP)"
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="Descuento Personal (%)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Perfil de Precios de Usuario"
        verbose_name_plural = "Perfiles de Precios de Usuario"
    
    def __str__(self):
        return f"{self.user.username} - Saldo: {self.balance} CUP"
    
    @property
    def available_credit(self):
        """Crédito disponible"""
        return max(0, self.credit_limit - self.balance)
    
    @property
    def can_make_purchase(self, amount):
        """Verifica si puede realizar una compra"""
        return (self.balance + amount) <= self.credit_limit
    
    def add_balance(self, amount):
        """Agrega saldo"""
        self.balance += amount
        self.last_payment_date = timezone.now()
        self.save()
    
    def deduct_balance(self, amount):
        """Deduce saldo"""
        if not self.can_make_purchase(amount):
            raise ValueError("Saldo insuficiente")
        self.balance += amount  # Suma porque el balance es negativo (deuda)
        self.total_spent += amount
        self.save()
    
    def calculate_cost(self, hours, material_weight, material_type, user_role):
        """Calcula el costo de una impresión"""
        if not self.pricing_config:
            raise ValueError("No hay configuración de precios")
        
        # Horas mínimas de facturación
        billing_hours = max(hours, self.pricing_config.min_billing_hours)
        
        # Costo base
        base_cost = (
            billing_hours * self.pricing_config.cost_per_hour +
            material_weight * self.pricing_config.cost_per_gram
        )
        
        # Aplicar multiplicador de material
        material_multiplier = self.pricing_config.get_material_multiplier(material_type)
        material_cost = base_cost * material_multiplier
        
        # Aplicar descuento por rol
        role_discount = self.pricing_config.get_role_discount(user_role)
        discounted_cost = material_cost * (1 - role_discount)
        
        # Aplicar descuento personal
        final_cost = discounted_cost * (1 - self.discount_percentage / 100)
        
        return round(final_cost, 2)


class PrintJob(models.Model):
    """Trabajos de impresión 3D"""
    job_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        verbose_name="ID del Trabajo"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='print_jobs',
        verbose_name="Usuario"
    )
    printer = models.ForeignKey(
        Printer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='print_jobs',
        verbose_name="Impresora"
    )
    
    # Información del trabajo
    file_name = models.CharField(max_length=255, verbose_name="Nombre del Archivo")
    file_size = models.IntegerField(verbose_name="Tamaño del Archivo (bytes)")
    file_url = models.URLField(
        max_length=500,
        blank=True,
        verbose_name="URL del Archivo"
    )
    material_type = models.CharField(
        max_length=3,
        choices=MaterialType.choices,
        default=MaterialType.PLA,
        verbose_name="Tipo de Material"
    )
    material_weight = models.FloatField(
        verbose_name="Peso del Material (g)",
        validators=[MinValueValidator(0.1)]
    )
    estimated_hours = models.FloatField(
        verbose_name="Horas Estimadas",
        validators=[MinValueValidator(0.1)]
    )
    actual_hours = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Horas Reales"
    )
    
    # Especificaciones de impresión
    layer_height = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Altura de Capa (mm)"
    )
    infill_percentage = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Porcentaje de Relleno (%)"
    )
    supports = models.BooleanField(default=False, verbose_name="Usa Soporte")
    
    # Estado y seguimiento
    status = models.CharField(
        max_length=3,
        choices=JobStatus.choices,
        default=JobStatus.PENDING,
        verbose_name="Estado"
    )
    priority = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name="Prioridad (1-10)"
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_jobs',
        verbose_name="Aprobado por"
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="Aprobado en")
    
    # Tiempos
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="Iniciado en")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Completado en")
    cancelled_at = models.DateTimeField(null=True, blank=True, verbose_name="Cancelado en")
    
    # Costos
    estimated_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Costo Estimado (CUP)"
    )
    actual_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Costo Real (CUP)"
    )
    paid = models.BooleanField(default=False, verbose_name="Pagado")
    
    # Notas y errores
    notes = models.TextField(blank=True, verbose_name="Notas")
    error_message = models.TextField(blank=True, verbose_name="Mensaje de Error")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Trabajo de Impresión"
        verbose_name_plural = "Trabajos de Impresión"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Job {self.job_id} - {self.get_status_display()}"
    
    @property
    def job_duration(self):
        """Duración del trabajo en horas"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() / 3600
        return None
    
    @property
    def can_start(self):
        """Verifica si el trabajo puede iniciar"""
        return (
            self.status == JobStatus.APPROVED and
            self.printer and
            self.printer.can_print
        )
    
    @property
    def can_cancel(self):
        """Verifica si el trabajo puede cancelarse"""
        return self.status in [JobStatus.PENDING, JobStatus.APPROVED, JobStatus.PRINTING]
    
    @property
    def is_completed(self):
        return self.status == JobStatus.COMPLETED
    
    @property
    def is_failed(self):
        return self.status == JobStatus.FAILED
    
    def calculate_estimated_cost(self):
        """Calcula el costo estimado"""
        try:
            profile = self.user.profile
            pricing_profile = self.user.pricing_profile
            
            return pricing_profile.calculate_cost(
                hours=self.estimated_hours,
                material_weight=self.material_weight,
                material_type=self.material_type,
                user_role=profile.role
            )
        except Exception as e:
            return None
    
    def start_printing(self):
        """Inicia la impresión"""
        if not self.can_start:
            raise ValueError("No se puede iniciar la impresión")
        
        self.status = JobStatus.PRINTING
        self.started_at = timezone.now()
        self.printer.status = PrinterStatus.PRINTING
        self.printer.save()
        self.save()
    
    def complete_job(self, actual_hours):
        """Completa el trabajo"""
        if self.status != JobStatus.PRINTING:
            raise ValueError("El trabajo no está en impresión")
        
        self.status = JobStatus.COMPLETED
        self.actual_hours = actual_hours
        self.completed_at = timezone.now()
        
        # Actualizar horas de la impresora
        if self.printer:
            self.printer.update_print_hours(actual_hours)
            self.printer.status = PrinterStatus.AVAILABLE
            self.printer.save()
        
        # Calcular costo real
        try:
            profile = self.user.profile
            pricing_profile = self.user.pricing_profile
            self.actual_cost = pricing_profile.calculate_cost(
                hours=actual_hours,
                material_weight=self.material_weight,
                material_type=self.material_type,
                user_role=profile.role
            )
        except Exception:
            pass
        
        self.save()
    
    def fail_job(self, error_message):
        """Marca el trabajo como fallido"""
        self.status = JobStatus.FAILED
        self.error_message = error_message
        self.completed_at = timezone.now()
        
        if self.printer:
            self.printer.status = PrinterStatus.AVAILABLE
            self.printer.save()
        
        self.save()


class SystemLog(models.Model):
    """Logs de auditoría del sistema"""
    log_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='system_logs',
        verbose_name="Usuario"
    )
    action = models.CharField(
        max_length=3,
        choices=LogAction.choices,
        verbose_name="Acción"
    )
    model_name = models.CharField(
        max_length=100,
        verbose_name="Nombre del Modelo"
    )
    object_id = models.CharField(
        max_length=100,
        verbose_name="ID del Objeto"
    )
    description = models.TextField(verbose_name="Descripción")
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Dirección IP"
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name="User Agent"
    )
    
    # Datos antes y después (para auditoría)
    before_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Datos Antes"
    )
    after_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Datos Después"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Log del Sistema"
        verbose_name_plural = "Logs del Sistema"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['model_name', 'object_id']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.model_name}:{self.object_id} - {self.created_at}"
    
    @classmethod
    def create_log(cls, user, action, model_name, object_id, description='', 
                   before_data=None, after_data=None, request=None):
        """Método helper para crear logs"""
        log = cls.objects.create(
            user=user,
            action=action,
            model_name=model_name,
            object_id=str(object_id),
            description=description,
            before_data=before_data,
            after_data=after_data
        )
        
        if request:
            log.ip_address = request.META.get('REMOTE_ADDR')
            log.user_agent = request.META.get('HTTP_USER_AGENT', '')
            log.save()
        
        return log
    
    @property
    def summary(self):
        """Resumen corto del log"""
        user_info = self.user.username if self.user else "Sistema"
        return f"{user_info} - {self.get_action_display()} - {self.model_name}"
