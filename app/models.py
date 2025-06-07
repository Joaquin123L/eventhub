from django.contrib.auth.models import AbstractUser
from django.db import models
from datetime import datetime
from django.db.models import Sum
from django.utils import timezone


class User(AbstractUser):
    is_organizer = models.BooleanField(default=False)

    @classmethod
    def validate_new_user(cls, email, username, password, password_confirm):
        errors = {}

        if email is None:
            errors["email"] = "El email es requerido"
        elif User.objects.filter(email=email).exists():
            errors["email"] = "Ya existe un usuario con este email"

        if username is None:
            errors["username"] = "El username es requerido"
        elif User.objects.filter(username=username).exists():
            errors["username"] = "Ya existe un usuario con este nombre de usuario"

        if password is None or password_confirm is None:
            errors["password"] = "Las contraseñas son requeridas"
        elif password != password_confirm:
            errors["password"] = "Las contraseñas no coinciden"

        return errors


class Event(models.Model):
    STATUS_CHOICES = [
        ("Activo", "Activo"),
        ("Cancelado", "Cancelado"),
        ("Reprogramado", "Reprogramado"),
        ("Agotado", "Agotado"),
        ("Finalizado", "Finalizado"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    scheduled_at = models.DateTimeField()
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="organized_events")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    category = models.ForeignKey('Category', on_delete=models.PROTECT, related_name="events", null=True, blank=True)
    venue = models.ForeignKey('Venue', on_delete=models.CASCADE, related_name='events', null=True, blank=True)
    capacity = models.IntegerField(default=0, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Activo")

    @property
    def countdown(self):
        now = timezone.now()
        if self.scheduled_at > now and self.status not in ["Cancelado", "Finalizado"]:
            return self.scheduled_at - now
        return None
    
    @property
    def es_pasado(self):
        return self.scheduled_at < timezone.now()

    def is_organizer(self, user):
        return self.organizer == user

    def check_and_update_agotado(self):
        total = self.tickets.aggregate(total=Sum('quantity'))['total'] or 0 # type: ignore
        total = int(total) if total is not None else 0
        capacity = int(self.capacity) if self.capacity is not None else 0

        if total >= capacity:
            if self.status != "Agotado":
                self.status = "Agotado"
                self.save()
        else:
            if self.status == "Agotado":
                self.status = "Activo"
                self.save()

    def __str__(self):
        return self.title

    def check_and_update_status(self):
        if self.status != "Cancelado":
            if self.scheduled_at < timezone.now():
                self.status = "Finalizado"
                self.save()
            elif self.capacity is not None and self.capacity <= 0:
                self.status = "Agotado"
                self.save()

    @classmethod
    def validate(cls, title, description, scheduled_at, capacity=None):
        errors = {}

        if title == "":
            errors["title"] = "Por favor ingrese un titulo"

        if description == "":
            errors["description"] = "Por favor ingrese una descripcion"
        
        if scheduled_at < timezone.now():
            errors["scheduled_at"] = "La fecha y hora del evento deben ser posteriores a la actual"

        if capacity is not None and capacity <= 0:
            errors["capacity"] = "La capacidad debe ser mayor a 0"

        return errors

    @classmethod
    def new(cls, title, description, scheduled_at, organizer, category=None, venue=None, capacity=None):
        errors = cls.validate(title, description, scheduled_at, capacity)

        if errors:
            return False, errors

        event = cls.objects.create(
            title=title,
            description=description,
            scheduled_at=scheduled_at,
            organizer=organizer,
            category=category,
            venue=venue,
            capacity=capacity,
            status="Activo"
        )

        event.check_and_update_status()
        return True, None

    def update(self, title, description, scheduled_at, organizer, category=None, venue=None, capacity=None):
        # Guardamos los valores anteriores
        old_scheduled_at = self.scheduled_at
        old_venue = self.venue

        # Usar los valores actuales si no se pasan nuevos
        new_title = title or self.title
        new_description = description or self.description
        new_scheduled_at = scheduled_at or self.scheduled_at
        
        errors = Event.validate(new_title, new_description, new_scheduled_at)

        if len(errors.keys()) > 0:
            return False, errors
        
        self.title = title or self.title
        self.description = description or self.description
        self.scheduled_at = scheduled_at or self.scheduled_at
        self.organizer = organizer or self.organizer
        self.category = category if category is not None else self.category
        self.venue = venue if venue is not None else self.venue
        self.capacity = capacity if capacity is not None else self.capacity

        # Cambio de fecha/lugar
        hubo_cambio_fecha = old_scheduled_at != self.scheduled_at
        hubo_cambio_lugar = old_venue != self.venue
        if hubo_cambio_fecha and self.status != "Cancelado":
            self.status = "Reprogramado"

        if hubo_cambio_fecha or hubo_cambio_lugar:
            self.notify_changes(old_scheduled_at=old_scheduled_at, old_venue=old_venue)

        self.save()
        self.check_and_update_status()

        return True, None

    def notify_changes(self, old_scheduled_at=None, old_venue=None):
        cambios = []

        if old_scheduled_at and old_scheduled_at != self.scheduled_at:
            cambios.append(
                f"Fecha/Hora: de {old_scheduled_at.strftime('%d/%m/%Y %H:%M')} "
                f"a {self.scheduled_at.strftime('%d/%m/%Y %H:%M')}"
            )

        if old_venue and old_venue != self.venue:
            old_name = old_venue.name if old_venue else 'sin lugar'
            new_name = self.venue.name if self.venue else 'sin lugar'
            cambios.append(f"Lugar: de {old_name} a {new_name}")

        if not cambios:
            return

        usuarios = User.objects.filter(tickets__event=self).distinct()

        titulo = "Cambio en evento"
        mensaje = f"Se han realizado cambios en el evento '{self.title}':\n\n" + "\n".join(cambios)
        prioridad = "HIGH"

        Notification.new(titulo, mensaje, prioridad, usuarios, event=self)

class Category(models.Model):
    name =models.CharField(max_length=100)
    description = models.TextField()
    is_active = models.BooleanField(default=True)

    @classmethod
    def validate(cls, name, description):
        errors = {}

        if name == "":
            errors["name"] = "Por favor ingrese un nombre"

        if description == "":
            errors["description"] = "Por favor ingrese una descripcion"

        return errors

    @classmethod
    def new(cls, name, description):
        errors = Category.validate(name, description)

        if len(errors.keys()) > 0:
            return False, errors

        Category.objects.create(
            name=name,
            description=description,
        )

        return True, None
    def update(self, name, description):
        self.name = name or self.name
        self.description = description or self.description

        self.save()

class Comment(models.Model):
    title = models.CharField(max_length=100)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="comments")

    @classmethod
    def validate(cls, title, text):
        errors = {}

        if not title or title.strip() == "":
            errors["title"] = "El título es requerido"

        if not text or text.strip() == "":
            errors["text"] = "El texto es requerido"

        return errors

    @classmethod
    def new(cls, title, text, user, event):
        errors = cls.validate(title, text)

        if errors:
            return False, errors

        cls.objects.create(
            title=title.strip(),
            text=text.strip(),
            user=user,
            event=event
        )

        return True, None

    def update(self, title, text):
        self.title = title.strip() if title else self.title
        self.text = text.strip() if text else self.text
        self.save()

class Venue(models.Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    capacity = models.IntegerField(blank=True, null=True)  # Cambiar a IntegerField
    contact = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name


class Ticket(models.Model):
    buy_date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tickets")
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="tickets")
    ticket_code = models.CharField(max_length=100, unique=True)
    quantity = models.IntegerField(default=1)
    type = models.CharField(max_length=50, choices=[('general', 'General'), ('vip', 'VIP')], default='general')

    @classmethod
    def validate(cls, ticket_code, quantity):
        errors = {}

        if ticket_code is None or ticket_code == "":
            errors["ticket_code"] = "El código de entrada es requerido"

        if quantity is None or quantity <= 0:
            errors["quantity"] = "La cantidad debe ser mayor a 0"

        return errors

    @classmethod
    def new(cls, ticket_code, quantity, user, event):
        errors = cls.validate(ticket_code, quantity)

        if len(errors.keys()) > 0:
            return False, errors

        Ticket.objects.create(
            ticket_code=ticket_code,
            quantity=quantity,
            user=user,
            event=event
        )

    def update(self, type, quantity):
        self.type = type or self.type
        self.quantity = quantity or self.quantity

        self.save()

class Rating(models.Model):
    title = models.CharField(max_length=100)
    text = models.TextField()
    rating = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ratings")
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="ratings")

    @classmethod
    def validate(cls, rating,title):
        errors = {}

        if rating is None:
            errors["rating"] = "La calificación es requerida"
        elif rating < 1 or rating > 5:
            errors["rating"] = "La calificación debe estar entre 1 y 5"

        if title is None or title.strip() == "":
            errors["title"] = "El título es requerido"



        return errors

    @classmethod
    def new(cls, title, text, rating, user, event):
        errors = cls.validate(rating, title)

        if errors:
            return False, errors

        cls.objects.create(
            title=title,
            text=text,
            rating=rating,
            user=user,
            event=event
        )

        return True, None

    def update(self, rating, title, text):
        self.rating = rating if rating is not None else self.rating
        self.title = title.strip() if title else self.title
        self.text = text.strip() if text else self.text
        self.save()


class RefoundStatus(models.TextChoices):
    PENDING = "pending", "Pendiente"
    APPROVED = "approved", "Aprobado"
    REJECTED = "rejected", "Rechazado"

class RefoundReason(models.TextChoices):
    EVENT_CANCELLED = "event_cancelled", "Evento cancelado"
    TICKET_NOT_RECEIVED = "ticket_not_received", "Entrada no recibida"
    OTHER = "other", "Otro"

class RefoundRequest(models.Model):
    approved = models.BooleanField(default=False)
    approval_date = models.DateTimeField(null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=RefoundStatus.choices, default=RefoundStatus.PENDING)
    refound_reason = models.CharField(max_length=50, choices=RefoundReason.choices, default=RefoundReason.OTHER)
    ticket_code = models.CharField(max_length=100, unique=True)
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="refound_requests", null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="refound_requests")
    created_at = models.DateTimeField(auto_now_add=True)


    @classmethod
    def new(cls, amount, reason, refound_reason, ticket_code, user, status):
        if cls.objects.filter(user=user, status=RefoundStatus.PENDING).exists():
            return False, {"ATENCION": "Ya tenés una solicitud de reembolso pendiente. Cuando se resuelva podra solicitar otra."}

        errors = cls.validate(amount, reason, status, refound_reason, ticket_code, user)

        if errors:
            return False, errors

        cls.objects.create(
            amount=amount,
            reason=reason,
            refound_reason=refound_reason,
            ticket_code=ticket_code,
            user=user,
            status=status,
            ticket=Ticket.objects.get(ticket_code=ticket_code)
        )

        return True, None

    @classmethod
    def validate(cls, amount, reason, status, refound_reason, ticket_code, user):
        errors = {}

        if amount is None or amount < 0:
            errors["amount"] = "El monto debe ser mayor a 0."

        if reason is None or reason.strip() == "":
            errors["Detalles"] = "Se necesita ingresar los detalles adicionales del motivo."
        elif len(reason) > 500:
            errors["Detalles"] = "Los detalles no pueden superar los 500 caracteres."

        if status not in RefoundStatus.values:
            errors["status"] = "Estado inválido."

        if refound_reason not in RefoundReason.values:
            errors["Motivo del reembolso"] = "Motivo de reembolso inválido."

        if ticket_code is None:
            errors["ticket_code"] = "Debe asociarse un ticket."
        elif not Ticket.objects.filter(ticket_code=ticket_code).exists():
            errors["ticket_code"] = "El ticket no existe."

        if user is None:
            errors["user"] = "Debe asociarse un usuario."
        elif not User.objects.filter(id=user.id).exists():
            errors["user"] = "El usuario no existe."

        return errors

    def update(self, reason=None, refound_reason=None, status=None, approved=None):

        self.reason = reason.strip() if reason else self.reason
        self.refound_reason = refound_reason or self.refound_reason
        self.status = status or self.status
        self.approved = approved if approved is not None else self.approved

        if self.approved:
            self.approval_date = datetime.now()
            self.status = RefoundStatus.APPROVED

        self.save()

class Notification(models.Model):
    PRIORITY_CHOICES = [
        ("HIGH", "Alta"),
        ("MEDIUM", "Media"),
        ("LOW", "Baja"),
    ]

    title = models.CharField(max_length=50)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES)

    users = models.ManyToManyField(
        User,
        related_name="notifications",
        through='NotificationUser'
    )

    event = models.ForeignKey(
        'Event',
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,  # Añadí null=True para que sea opcional
        blank=True  # Añadí blank=True para formularios
    )

    def __str__(self):
        user_count = self.users.count()

        if user_count == 1:
            user = self.users.first()
            if user is None:  # por seguridad si se elimina de la bbdd.
                return f"Notificación: {self.title} con un usuario inconsistente"
            return f"Notificación: {self.title} para {user.username}"
        else:
            return f"Notificación: {self.title} para {user_count} usuarios"


    @classmethod
    def validate(cls, title, message, priority, users= None):
        errors = {}

        if not title:
            errors["title"] = "Por favor ingrese un título"
        if not message:
            errors["message"] = "Por favor ingrese un mensaje"
        if priority not in dict(cls.PRIORITY_CHOICES):
            errors["priority"] = "Prioridad inválida"
        # Validación de usuarios
        if not users:
            errors["users"] = "Debe proporcionar al menos un usuario"

        return errors

    @classmethod
    def new(cls, title, message, priority, users, event=None):
        errors = cls.validate(title, message, priority,users)

        if errors:
            return False, errors

        # Creamos la notificación
        notification = cls.objects.create(
            title=title,
            message=message,
            priority=priority,
            event=event # Django se encarga del id internamente
        )

#Esto actualiza la relación ManyToMany a través de la tabla intermedia 'NotificationUser
        notification.users.set(users)

        return True, None

    def update(self, title=None, message=None, priority=None, users=None, event=None):
        self.title = title or self.title
        self.message = message or self.message
        self.priority = priority or self.priority

        # Actualizar el evento si se proporciona uno nuevo
        if event is not None:
            self.event_id = event.id

        self.save()

        if users is not None:
            # Actualizar la relación directa
            self.users.set(users)
            # Eliminar relaciones anteriores
            NotificationUser.objects.filter(notification=self).delete()

            # Crear nuevas relaciones
            for user in users:
                NotificationUser.objects.create(user=user, notification=self)

class NotificationUser(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    notification = models.ForeignKey('Notification', on_delete=models.CASCADE)
    read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'notification')

class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorites")
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="favorites")

    class Meta:
        unique_together = ('user', 'event')

class SatisfactionSurvey(models.Model):
    ticket = models.OneToOneField(Ticket, on_delete=models.CASCADE)

    satisfaction_level = models.IntegerField(choices=[(1, 'Muy insatisfecho'), (2, 'Insatisfecho'), (3, 'Neutral'), (4, 'Satisfecho'), (5, 'Muy satisfecho')])
    ease_of_search = models.IntegerField(choices=[(1, 'Muy difícil'), (2, 'Difícil'), (3, 'Neutral'), (4, 'Fácil'), (5, 'Muy fácil')])
    payment_experience = models.IntegerField(choices=[(1, 'Muy malo'), (2, 'Malo'), (3, 'Aceptable'), (4, 'Bueno'), (5, 'Excelente')])
    received_ticket = models.BooleanField()
    would_recommend = models.IntegerField(choices=[(1, 'Definitivamente no'), (2, 'Probablemente no'), (3, 'No estoy seguro/a'), (4, 'Probablemente sí'), (5, 'Definitivamente sí')])

    additional_comments = models.TextField(blank=True)

