import datetime
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Exists, OuterRef
from django.http import HttpResponseForbidden, HttpResponseRedirect, HttpResponseBadRequest
from .models import Event, User, Category, Comment, Venue, Ticket, Rating, RefoundRequest, RefoundReason, RefoundStatus, \
    Notification, NotificationUser, Favorite, SatisfactionSurvey
from django.contrib import messages
import re
import random
from django.db import IntegrityError
from django.utils.timezone import now
from django.db.models import Sum
from django.db.models import Avg



def register(request):
    if request.method == "POST":
        email = request.POST.get("email")
        username = request.POST.get("username")
        is_organizer = request.POST.get("is-organizer") is not None
        password = request.POST.get("password")
        password_confirm = request.POST.get("password-confirm")

        errors = User.validate_new_user(email, username, password, password_confirm)

        if len(errors) > 0:
            return render(
                request,
                "accounts/register.html",
                {
                    "errors": errors,
                    "data": request.POST,
                },
            )
        else:
            user = User.objects.create_user(
                email=email, username=username, password=password, is_organizer=is_organizer
            )
            login(request, user)
            return redirect("events")

    return render(request, "accounts/register.html", {})


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is None:
            return render(
                request, "accounts/login.html", {"error": "Usuario o contraseña incorrectos"}
            )

        login(request, user)
        return redirect("events")

    return render(request, "accounts/login.html")


@login_required
def home(request):
    return render(request, "home.html", {
        "user_is_organizer": request.user.is_organizer
    })



@login_required
def event_detail(request, id):
    event = get_object_or_404(Event, pk=id)
    event.check_and_update_status()
    countdown = event.countdown
    tickets_vendidos = Ticket.objects.filter(event=event).aggregate(total=Sum('quantity'))['total'] or 0

    if countdown is not None:
        total_seconds = int(countdown.total_seconds())
        days = total_seconds // (24 * 3600)
        hours = (total_seconds % (24 * 3600)) // 3600
        minutes = (total_seconds % 3600) // 60
    else:
        days = hours = minutes = 0


    # Porcentaje de ocupación
    if event.capacity is None or event.capacity == 0:
        porcentaje_ocupado = 0
    else:
        porcentaje_ocupado = (tickets_vendidos / event.capacity) * 100
    todos_los_comentarios = Comment.objects.filter(event=event).order_by('-created_at')
    ratings = Rating.objects.filter(event=event).order_by('-created_at')
    tiene_ticket = Ticket.objects.filter(user=request.user, event=event).exists()
    promedio_rating = Rating.objects.filter(event=event).aggregate(Avg('rating'))['rating__avg'] or 0
    porcentaje_rating = round(promedio_rating * 20, 2)  # Escala de 0 a 100
    tiene_resena = Rating.objects.filter(user=request.user, event=event).exists()

    return render(request, "app/event_detail.html", {"event": event, "todos_los_comentarios": todos_los_comentarios, "ratings": ratings, "user_is_organizer": request.user.is_organizer, "porcentaje_ocupado": porcentaje_ocupado, "tickets_vendidos": tickets_vendidos, "tiene_ticket": tiene_ticket, "promedio_rating": promedio_rating, "porcentaje_rating": porcentaje_rating, "tiene_resena": tiene_resena,"countdown": countdown,  "countdown_days": days,
        "countdown_hours": hours,"countdown_minutes": minutes,})




@login_required
def event_delete(request, id):
    user = request.user
    if not user.is_organizer:
        return redirect("events")

    if request.method == "POST":
        event = get_object_or_404(Event, pk=id)
        event.delete()
        return redirect("events")

    return redirect("events")


@login_required
def event_form(request, id=None):
    user = request.user

    if not user.is_organizer:
        return redirect("events")

    if request.method == "POST":
        id = request.POST.get("id")
        title = request.POST.get("title")
        description = request.POST.get("description")
        date = request.POST.get("date")
        time = request.POST.get("time")
        category_id = request.POST.get("category")
        venue_id = request.POST.get("venue")
        capacity = request.POST.get("capacity")

        [year, month, day] = date.split("-")
        [hour, minutes] = time.split(":")

        scheduled_at = timezone.make_aware(
            datetime.datetime(int(year), int(month), int(day), int(hour), int(minutes))
        )

        category = get_object_or_404(Category, pk=category_id)
        venue = get_object_or_404(Venue, pk=venue_id)
        capacity = int(request.POST.get("capacity") or 0)
        #si la capacity es mayor a la capacidad del venue, se muestra un error
        if venue.capacity is not None and capacity > venue.capacity:
            categories = Category.objects.filter(is_active=True)
            venues = Venue.objects.all()
            error = f"La capacidad del evento ({capacity}) excede la del lugar ({venue.capacity})."
            return render(
                request,
                "app/event_form.html",
                {
                    "error": error,
                    "categories": categories,
                    "venues": venues,
                }
            )

        if id is None:
            success, errors = Event.new(title, description, scheduled_at, request.user, category, venue,capacity)
        else:

            event = get_object_or_404(Event, pk=id)
            # Guardamos los valores anteriores
            old_scheduled_at = event.scheduled_at
            old_venue_id = event.venue.id if event.venue else None            # Validamos antes de actualizar

            success, errors = event.update(title, description, scheduled_at, request.user, category, venue, capacity)
            if success:
                new_venue_id = getattr(venue, 'id', None)
                hubo_cambio_fecha_lugar = old_scheduled_at != scheduled_at or old_venue_id != new_venue_id
                if hubo_cambio_fecha_lugar:
                    usuarios = User.objects.filter(tickets__event=event).distinct()
                    cambios = []
                    if old_scheduled_at != scheduled_at:
                        cambios.append(
                            f"Fecha/Hora: de {old_scheduled_at.strftime('%d/%m/%Y %H:%M')} a {scheduled_at.strftime('%d/%m/%Y %H:%M')}"
                        )
                    if old_venue_id != new_venue_id:
                        old_venue = Venue.objects.get(pk=old_venue_id) if old_venue_id else None
                        cambios.append(
                            f"Lugar: de {old_venue.name if old_venue else 'sin lugar'} a {venue.name}"
                        )

                    detalles_cambios = "\n".join(cambios)
                    titulo = "Cambio en evento"
                    mensaje = f"Se han realizado cambios en el evento {event.title}: \n\n{detalles_cambios}"
                    prioridad = "HIGH"
                    Notification.new(titulo, mensaje, prioridad, usuarios, event)
        if success:
            return redirect("events")

        # Si hubo errores
        event_data = {
            "id": id,
            "title": title,
            "description": description,
            "scheduled_at": scheduled_at,
            "category": category,
            "venue": venue,
            "capacity":capacity,
        }

        categories = Category.objects.filter(is_active=True)
        venues = Venue.objects.all()
        return render(
            request,
            "app/event_form.html",
            {
                "event": event_data,
                "errors": errors,
                "user_is_organizer": user.is_organizer,
                "categories": categories,
                "venues": venues,
            },
        )

    event = {}
    if id is not None:
        event = get_object_or_404(Event, pk=id)

    categories = Category.objects.filter(is_active=True)
    venues = Venue.objects.all()

    return render(
        request,
        "app/event_form.html",
        {"event": event, "user_is_organizer": request.user.is_organizer, "categories": categories, "venues": venues},
    )

@login_required
def events(request):
    user = request.user
    order = request.GET.get("order", "asc")
    category_id = request.GET.get("category")
    venue_id = request.GET.get("venue")
    favorites_only = request.GET.get("favorites_only") == "on"
    ver_pasados = request.GET.get("ver_pasados") == "on"


    if user.is_organizer:
        events = Event.objects.filter(organizer=user)
        if not ver_pasados:
            events = events.filter(scheduled_at__gte=timezone.now()).exclude(status__in=["Cancelado", "Finalizado"])
    else:
        events = Event.objects.filter(scheduled_at__gte=timezone.now()).exclude(status__in=["Cancelado", "Finalizado"])

    if category_id:
        events = events.filter(category_id=category_id)

    if venue_id:
        events = events.filter(venue_id=venue_id)

    if favorites_only:
        events = events.filter(favorites__user=user)
    else:
        events = events.annotate(is_favorite=Exists(Favorite.objects.filter(user=user, event=OuterRef('pk'))))

    if order == "desc":
        events = events.order_by("-scheduled_at")
    else:
        events = events.order_by("scheduled_at")

    favorite_event_ids = set(
        Favorite.objects.filter(user=user).values_list("event_id", flat=True)
    )
    for event in events:
        event.is_favorite = event.pk in favorite_event_ids # type: ignore

    categories = Category.objects.filter(is_active=True)
    venues = Venue.objects.all()

    return render(
        request,
        "app/events.html",
        {
            "events": events,
            "categories": categories,
            "venues": venues,
            "selected_category": category_id,
            "selected_venue": venue_id,
            "order": order,
            "user_is_organizer": user.is_organizer,
            "favorites_only": favorites_only,
            "ver_pasados": ver_pasados,
        },
    )




def categorias(request):
    category_list = Category.objects.annotate(num_events=Count('events'))

    return render(request, "app/categories.html",
                    {"categorys": category_list, "user_is_organizer": request.user.is_organizer})

def category_form(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')

        category = Category.objects.create(name=name, description=description)

        return redirect('categorias')

    return render(request, 'app/category_form.html')


def edit_category(request, id):
    category = get_object_or_404(Category, id=id)

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        if name and description:
            category.name = name
            category.description = description
            category.save()
            return redirect('categorias')
        else:
            return render(request, 'app/category_edit.html', {
                'category': category,
                'error': 'Todos los campos son obligatorios.'
            })

    return render(request, 'app/category_edit.html', {'category': category})

def category_delete(request, id):
    user = request.user
    if not user.is_organizer:
        return redirect("categorias")

    if request.method == "POST":
        category = get_object_or_404(Category, pk=id)

        try:
            category.delete()
            messages.success(request, "Categoría eliminada exitosamente.")
        except IntegrityError:
            messages.warning(request, "No se puede eliminar esta categoría porque tiene eventos asociados.")

        return redirect("categorias")

    return redirect("categorias")

def crear_comentario(request, event_id):
    evento = get_object_or_404(Event, id=event_id)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        text = request.POST.get('text', '').strip()
        comentario_id = request.POST.get('comentario_id')  # nuevo

        errors = Comment.validate(title, text)

        if errors:
            return render(request, "app/event_detail.html", {
                "event": evento,
                "errors": errors,
                "title": title,
                "text": text,
            })

        if comentario_id:
            # Si hay comentario_id, es edición
            comentario = get_object_or_404(Comment, id=comentario_id)
            if request.user != comentario.user:
                return HttpResponseForbidden("No podés editar este comentario")

            comentario.update(title, text)
            messages.success(request, "Comentario editado exitosamente")
        else:
            # Si no hay comentario_id, se crea uno nuevo
            Comment.objects.create(
                title=title,
                text=text,
                user=request.user,
                event=evento
            )
            messages.success(request, "Comentario creado exitosamente")

        return redirect('event_detail', id=event_id)

    return redirect('event_detail', id=event_id)



def delete_comment(request, event_id, pk):
    comment = get_object_or_404(Comment, pk=pk, event_id=event_id)

    # Verificación de permisos
    if request.user == comment.user or request.user == comment.event.organizer:
        comment.delete()
        messages.success(request, "Comentario eliminado correctamente")
    else:
        messages.error(request, "No tienes permiso para esta acción")

    return redirect('event_detail', id=event_id)

@login_required
def organizer_comments(request):
    user = request.user

    if not user.is_organizer:
        # Si no es organizador, lo podemos redirigir o mostrar error
        return render(request, "no_permission.html")

    # Busco todos los comentarios de los eventos que organiza
    comments = Comment.objects.filter(event__organizer=user).select_related('event', 'user')

    context = {
        'comments': comments,
        'user_is_organizer': True  # <<< agregamos esto
    }

    return render(request, 'app/organizer_comments.html', context)

@login_required
def organizer_delete_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)

    # Verificación de permisos
    if request.user == comment.event.organizer:
        comment.delete()
        messages.success(request, "Comentario eliminado correctamente")
    else:
        messages.error(request, "No tienes permiso para esta acción")

    return redirect('organizer_comments')

#------------------VENUES-----------------
#listar venues
@login_required
def venue_list(request):
    if not request.user.is_organizer:
        return redirect('events')

    venues = Venue.objects.all()
    return render(request, 'app/venue_list.html', {'venues': venues, "user_is_organizer": request.user.is_organizer})

#crear venues
def venue_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        address = request.POST.get('address', '').strip()
        city = request.POST.get('city', '').strip()
        capacity = request.POST.get('capacity', '').strip()
        contact = request.POST.get('contact', '').strip()

        errors = []

        # Validaciones de longitud mínima para los campos string
        if len(name) < 3:
            errors.append('El nombre debe tener al menos 3 caracteres.')
        if len(address) < 3:
            errors.append('La dirección debe tener al menos 3 caracteres.')
        if len(city) < 3:
            errors.append('La ciudad debe tener al menos 3 caracteres.')
        if len(contact) < 3:
            errors.append('El contacto debe tener al menos 3 caracteres.')

        # Validación de capacidad
        if not capacity:
            errors.append('La capacidad es obligatoria.')
        else:
            try:
                capacity = int(capacity)
                if capacity <= 0:
                    errors.append('La capacidad debe ser un número positivo.')
            except ValueError:
                errors.append('La capacidad debe ser un número.')

        if errors:
            return render(request, 'app/venue_form.html', {
                'errors': errors,
                'venue': {
                    'name': name,
                    'address': address,
                    'city': city,
                    'capacity': capacity,
                    'contact': contact,
                }
            })

        Venue.objects.create(
            name=name,
            address=address,
            city=city,
            capacity=capacity,
            contact=contact
        )
        return redirect('venue_list')

    return render(request, 'app/venue_form.html')


# Editar locación existente
def venue_edit(request, pk):
    venue = get_object_or_404(Venue, pk=pk)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        address = request.POST.get('address', '').strip()
        city = request.POST.get('city', '').strip()
        capacity = request.POST.get('capacity', '').strip()
        contact = request.POST.get('contact', '').strip()

        errors = []

        # Validaciones de longitud mínima para los campos string
        if len(name) < 3:
            errors.append('El nombre debe tener al menos 3 caracteres.')
        if len(address) < 3:
            errors.append('La dirección debe tener al menos 3 caracteres.')
        if len(city) < 3:
            errors.append('La ciudad debe tener al menos 3 caracteres.')
        if len(contact) < 3:
            errors.append('El contacto debe tener al menos 3 caracteres.')

        # Validación de capacidad
        if not capacity:
            errors.append('La capacidad es obligatoria.')
        else:
            try:
                capacity = int(capacity)
                if capacity <= 0:
                    errors.append('La capacidad debe ser un número positivo.')
            except ValueError:
                errors.append('La capacidad debe ser un número.')

        if errors:
            return render(request, 'app/venue_form.html', {
                'errors': errors,
                'venue': {
                    'name': name,
                    'address': address,
                    'city': city,
                    'capacity': capacity,
                    'contact': contact,
                }
            })

        venue.name = name
        venue.address = address
        venue.city = city
        venue.capacity = capacity
        venue.contact = contact
        venue.save()

        return redirect('venue_list')

    return render(request, 'app/venue_form.html', {'venue': venue})

#borrar venues
def venue_delete(request, pk):
    venue = get_object_or_404(Venue, pk=pk)

    if request.method == 'POST':
        venue.delete()
        return redirect('venue_list')

    return render(request, 'app/venue_confirm_delete.html', {'venue': venue})


@login_required
def tickets(request, event_id):
    if not request.user.is_organizer:
        return redirect('events')
    #ocon el id del evento obtengo todos sus tickets
    tickets = Ticket.objects.filter(event_id=event_id).order_by('-buy_date')

    return render(
        request,
        "app/tickets.html",
        {"events": events, "user_is_organizer": request.user.is_organizer, "tickets": tickets},
    )

@login_required
def comprar_ticket(request, event_id):
    event = get_object_or_404(Event, pk=event_id)

    user = request.user
    tickets_previos = Ticket.objects.filter(user=user, event=event).aggregate(total=Sum('quantity'))['total'] or 0
    tickets_disponibles = max(0, 4 - tickets_previos)

    if request.method == 'POST':
        # Obtener datos del formulario
        ticket_code = request.POST.get('ticket_code')
        quantity = request.POST.get('quantity')
        type_entrada = request.POST.get('type')
        try:
            quantity = int(quantity)
        except ValueError:
            quantity = 0
        if quantity <= 0:
            messages.error(request, "La cantidad de entradas debe ser mayor a 0.")
            return render(request, 'app/ticket_compra.html', {
                'event': event,
                'event_id': event_id
            })

        if tickets_previos + quantity > 4:
            disponibles = max(0, 4 - tickets_previos)
            messages.error(
                request,
                f"No puedes comprar más de 4 entradas por evento. Ya compraste {tickets_previos} y solo puedes adquirir {disponibles} más."
            )
            return render(request, 'app/ticket_compra.html', {
                'event': event,
                'event_id': event_id
            })
                # Verificar si el evento está cancelado
        if event.status == "Cancelado":
            error = "No se pueden comprar entradas para un evento cancelado."
            return render(request, 'app/ticket_compra.html', {
                'event': event,
                'event_id': event_id,
                'error': error
            })
        # verificar si hay cupo, si no hay cupo se muestra un error que diga no quedan entradas
        if event.capacity is not None:
            tickets_vendidos = Ticket.objects.filter(event=event).aggregate(total=Sum('quantity'))['total'] or 0
            if tickets_vendidos + quantity > event.capacity:
                # mostrar cantidad de entradas disponibles
                tickets_disponibles = event.capacity - tickets_vendidos
                if tickets_disponibles == 0:
                    error = "No quedan entradas disponibles."
                else:
                    error = f"No quedan entradas disponibles. Solo quedan {tickets_disponibles} entradas."

                return render(request, 'app/ticket_compra.html', {
                    'event': event,
                    'event_id': event_id,
                    'error': error
                })
        # Datos de pago (estos se enviarían a una API externa en un caso real)
        payment_data = {
            'card_number': request.POST.get('card_number'),
            'card_expiry': request.POST.get('card_expiry'),
            'card_cvv': request.POST.get('card_cvv'),
            'card_name': request.POST.get('card_name'),
        }

        # Simulación de llamada a API de pago
        payment_success = simular_procesamiento_pago(payment_data)

        if not payment_success:
            messages.error(request, "Error en el procesamiento del pago. Por favor, intenta nuevamente.")
            return render(request, 'app/ticket_compra.html', {
                'event': event,
                'event_id': event_id,
                'error': "Error en el procesamiento del pago"
            })

        errors = Ticket.validate(ticket_code, quantity)

        if errors:
            messages.error(request, "Error en la validación del ticket.")
            return render(request, 'app/ticket_compra.html', {
                'errors': errors,
                'event': event,
                'event_id': event_id
            })

        user = request.user

        ticket = Ticket.objects.create(
            ticket_code=ticket_code,
            quantity=quantity,
            type=type_entrada,
            user=user,
            event=event
        )
        event.check_and_update_agotado()

        messages.success(request, f"¡Compra exitosa! Tu código de ticket es: {ticket_code}")
        return redirect('satisfaction_survey', ticket_id=ticket.pk)
    return render(request, 'app/ticket_compra.html', {
        'event': event,
        'event_id': event_id,
        'tickets_disponibles': tickets_disponibles
    })

def simular_procesamiento_pago(payment_data):
    """
    Función para simular el procesamiento de pago con una pasarela externa.
    En un entorno real, aquí se realizaría una llamada a la API de la pasarela de pagos.
    """
    card_number = payment_data.get('card_number', '').replace(' ', '')

    # Comprobar que el número de tarjeta tiene 16 dígitos
    if not card_number.isdigit() or len(card_number) != 16:
        return False

    # Comprobar que la fecha de expiración tiene el formato MM/AA
    expiry = payment_data.get('card_expiry', '')
    if not re.match(r'^\d{2}/\d{2}$', expiry):
        return False

    # Comprobar que el CVV tiene 3-4 dígitos
    cvv = payment_data.get('card_cvv', '')
    if not cvv.isdigit() or not (3 <= len(cvv) <= 4):
        return False

    # Simular un 100% de probabilidad de éxito en el pago
    return random.random() < 1.00

@login_required
def ticket_delete(request, event_id, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    event = ticket.event

    if request.method == 'POST':
        ticket.delete()
        event.check_and_update_agotado()
        messages.success(request, "Ticket eliminado correctamente")
        return redirect('tickets', event_id=event_id)

    return render(request, 'app/tickets', {'ticket': ticket})

@login_required
def mis_tickets(request):
    tickets = Ticket.objects.filter(user=request.user).order_by('-buy_date')

    for ticket in tickets:
        if ticket.type == "general":
            unit_price = 50
        elif ticket.type == "vip":
            unit_price = 100
        else:
            unit_price = 0

        setattr(ticket, 'unit_price', unit_price)
        setattr(ticket, 'total_price', unit_price * ticket.quantity)

    return render(request, 'app/mis_tickets.html', {'tickets': tickets})

@login_required
def update_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    # Verificamos si existe una solicitud de reembolso con el mismo ticket_code
    if RefoundRequest.objects.filter(ticket_code=ticket.ticket_code).exists():
        messages.error(request, "No se puede editar un ticket que tiene una solicitud de reembolso.")
        return redirect('Mis_tickets')

    #si el evento al que esta asociado el ticket tiene estado finalizado / cancelado, no se puede editar
    if ticket.event.status in ['Finalizado', 'Cancelado']:
        messages.error(request, "No se puede editar un ticket de un evento que ya no esta disponible.")
        return redirect('Mis_tickets')

    if request.method == 'POST':
        quantity = request.POST.get('quantity')
        type = request.POST.get('type')

        if quantity and type:
            try:
                quantity = int(quantity)
            except (TypeError, ValueError):
                messages.error(request, "Cantidad inválida.")
                return redirect('Mis_tickets')

            if quantity <= 0:
                messages.error(request, "La cantidad debe ser mayor que 0.")
                return redirect('Mis_tickets')

            # Verificar cuántos tickets tiene el usuario para este evento, excluyendo el actual
            tickets_previos = Ticket.objects.filter(
                user=ticket.user,
                event=ticket.event
            ).exclude(pk=ticket.pk).aggregate(total=Sum('quantity'))['total'] or 0

            if tickets_previos + quantity > 4:
                disponibles = max(0, 4 - tickets_previos)
                messages.error(
                    request,
                    f"No puedes tener más de 4 entradas por evento. Solo puedes actualizar a un máximo de {disponibles}."
                )
                return redirect('Mis_tickets')

            ticket.quantity = quantity
            ticket.type = type
            ticket.save()
            return redirect('Mis_tickets')

    return render(request, 'app/Mis_tickets.html', {'ticket': ticket})

@login_required
def event_cancel(request, pk):
    event = get_object_or_404(Event, pk=pk)

    # Verificamos que el usuario sea el organizador
    if request.user != event.organizer:
        return redirect('event_list')

    event.status = 'Cancelado'
    event.save()
    return redirect('events')

def rating_create(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if Rating.objects.filter(user=request.user, event=event).exists():
        messages.error(request, "Ya has calificado este evento")
        return redirect('event_detail', id=event_id)

    if not Ticket.objects.filter(user=request.user, event=event).exists():
        messages.error(request, "No puedes calificar un evento si no tienes un ticket")
        return redirect('event_detail', id=event_id)

    if request.method == 'POST':
        title = request.POST.get('title')
        text = request.POST.get('text')
        rating_value = request.POST.get('rating')
        rating_value = int(rating_value) if rating_value else None

        if rating_value is not None:
            Rating.objects.create(
                user=request.user,
                event=event,
                rating=rating_value,
                title=title,
                text=text
            )
            messages.success(request, "Calificación creada exitosamente",)
        else:
            messages.error(request, "Error al crear la calificación")

    return redirect('event_detail', id=event_id)

def rating_update(request, event_id, rating_id):
    event = get_object_or_404(Event, id=event_id)
    rating = get_object_or_404(Rating, id=rating_id, event=event)

    if request.user != rating.user:
        return HttpResponseForbidden("No tenes permiso para editar esta calificación")

    if request.method == 'POST':
        rating_value = request.POST.get('rating')
        rating_value = int(rating_value) if rating_value else None

        if rating_value is not None:
            rating.rating = rating_value
            rating.save()
            messages.success(request, "Calificación actualizada exitosamente")
        else:
            messages.error(request, "Error al actualizar la calificación")

    return redirect('event_detail', id=event_id)

def rating_delete(request, event_id, rating_id):
    event = get_object_or_404(Event, id=event_id)
    rating = get_object_or_404(Rating, id=rating_id, event=event)

    if not (request.user == rating.user or request.user == event.organizer):
        return HttpResponseForbidden("No tienes permiso para eliminar esta calificación")
    if request.method == 'POST':
        rating.delete()
        messages.success(request, "Calificación eliminada exitosamente")
    else:
        messages.error(request, "Error al eliminar la calificación")

    return redirect('event_detail', id=event_id)

@login_required
def create_refound(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    event_date = ticket.event.scheduled_at
    if event_date < timezone.now():
        messages.error(request, 'No se puede solicitar el reembolso: El evento ya pasó.')
        return redirect('Mis_tickets')

    if (event_date - timezone.now()) > datetime.timedelta(days=30):
        messages.error(request, 'No se puede solicitar el reembolso: Faltan más de 30 días para el evento.')
        return redirect('Mis_tickets')

    if request.method == 'POST':
        ticket_code = request.POST.get('ticket_code')
        reason = request.POST.get('reason')
        refound_reason = request.POST.get('refound_reason')
        status = RefoundStatus.PENDING
        amount = 0

        if (ticket.event.scheduled_at-timezone.now()) > datetime.timedelta(days=7):
            if ticket.type == 'general':
                amount = 50*ticket.quantity
            elif ticket.type == 'vip':
                amount = 100*ticket.quantity

        if datetime.timedelta(days=7) > (ticket.event.scheduled_at - timezone.now()) > datetime.timedelta(days=2):
            if ticket.type == 'general':
                amount = 25*ticket.quantity
            elif ticket.type == 'vip':
                amount = 50*ticket.quantity

        if (ticket.event.scheduled_at-timezone.now()) < datetime.timedelta(days=2):
            status = RefoundStatus.REJECTED

        success, errors = RefoundRequest.new(
            amount=float(amount),
            reason=reason,
            refound_reason=refound_reason,
            ticket_code=ticket_code,
            user=request.user,
            status=status
        )

        if not success:
            return render(request, 'app/refound_form.html', {
                'ticket': ticket,
                'refoundReason': RefoundReason,
                'errors': errors,
                'input': request.GET
            })

        return redirect('Mis_tickets')
    if request.method == 'GET':
        return render(request, 'app/refound_form.html', {
            'ticket': ticket,
            'refoundReason': RefoundReason
        })
    return redirect('Mis_tickets')

@login_required
def delete_refound(request, refound_id):
    refound = get_object_or_404(RefoundRequest, id=refound_id)
    if request.method == 'POST':
        refound.delete()
        messages.success(request, "Reembolso eliminado correctamente")
        return redirect('refound_user')
    return redirect('refound_user')

@login_required
def refound_user(request):
    user = request.user
    refounds = RefoundRequest.objects.filter(user=user).order_by('-created_at')
    return render(request, 'app/refound_user.html', {'refounds': refounds})

@login_required
def refound_detail(request, refound_id):
    refound = get_object_or_404(RefoundRequest, id=refound_id)

    if not request.user.is_organizer:
        return render(request, 'app/refound_detail.html', {'refound': refound})
    return render(request, 'app/refound_detail.html', {'refound': refound, 'user_is_organizer': True})

@login_required
def update_refound(request, refound_id):
    refound = get_object_or_404(RefoundRequest, id=refound_id)
    if request.method == 'POST':
        if refound.approved:
            return redirect('refound_user')
        refound.update(
            reason=request.POST.get('reason'),
            refound_reason=request.POST.get('refound_reason')
        )
        return redirect('refound_detail', refound_id=refound_id)

    if request.method == 'GET':
        return render(request, 'app/refound_update.html', {'refound': refound,
                                                            'refoundReason': RefoundReason})
    return redirect('refound_user')

@login_required
def refound_admin(request):
    if not request.user.is_organizer:
        return redirect('events')

    refounds = RefoundRequest.objects.all().order_by('-created_at')
    return render(request, 'app/refound_admin.html', {'refounds': refounds,
                                                    'user_is_organizer': True})

@login_required
def approve_or_reject_refound(request, refound_id):
    if not request.user.is_organizer:
        return redirect('events')

    refound = get_object_or_404(RefoundRequest, id=refound_id)
    if request.method == 'POST':
        if request.POST.get('action') == 'approve':
            refound.update(approved=True)
            messages.success(request, "Reembolso aprobado correctamente")
        elif request.POST.get('action') == 'reject':
            refound.update(approved=False, status=RefoundStatus.REJECTED)
            messages.success(request, "Reembolso rechazado correctamente")
        return redirect('refound_admin')
    return redirect('refound_admin')

# notificacion

def notification_form(request, id=None):
    User = get_user_model()
    if not request.user.is_organizer:
        return redirect("notification")

    notification = None
    if id is not None:
        notification = get_object_or_404(Notification, pk=id)

    if request.method == "POST":
        # Campos
        title = request.POST.get("title")
        message = request.POST.get("message")
        priority = request.POST.get("priority")
        event_id = request.POST.get("event")
        recipient_type = request.POST.get("recipient_type")
        user_ids = request.POST.getlist("users")

        event = get_object_or_404(Event, pk=event_id)

        #usuarios segun tipo de destinatario
        # Usuarios con tickets del evento seleccionado
        if recipient_type == "all":
            users = User.objects.filter(tickets__event=event).distinct()
            if not users.exists():
                return render(request, "app/notification_form.html", {
                    "events": Event.objects.filter(scheduled_at__gte=now()),
                    "users": User.objects.all(),
                    "errors": ["No hay asistentes al evento."],
                    "notification": notification,
                })
        else:
            user_ids = request.POST.getlist("users")
            users = User.objects.filter(id__in=user_ids, tickets__event=event).distinct()

        if id is None:  # Crear nueva notificación
            success, errors = Notification.new(
                title=title,
                message=message,
                priority=priority,
                users=users,
                event=event
            )

            if not success:
                return render(request, "app/notification_form.html", {
                    "events": Event.objects.filter(scheduled_at__gte=now()),
                    "users": User.objects.all(),
                    "errors": errors,
                    "notification": notification,
                })
        else:  # Actualizar notificación existente
                notification = get_object_or_404(Notification, pk=id)
                notification.update(
                title=title,
                message=message,
                priority=priority,
                users=users,
                event=event
                 )

        return redirect("notification")

    events = Event.objects.filter(scheduled_at__gte=now())
    users = User.objects.filter(
        tickets__event__in=events,
        tickets__event__scheduled_at__gte=now()
    ).distinct()

    return render(request, "app/notification_form.html", {
        "notification": notification,
        "events": events,
        "users": users,
        "user_is_organizer": request.user.is_organizer,
    })

@login_required
def notification(request):
    # Verifica si el usuario es un organizador
    if not request.user.is_organizer:
        # Si no es organizador, muestra un mensaje de error y redirige al inicio
        return redirect("home")

    # Obtener todos los eventos para el filtro
    events = Event.objects.all()

    # Configurar los filtros
    event_filter = request.GET.get('event', 'all')
    priority_filter = request.GET.get('priority', 'all')
    search_query = request.GET.get('search', '')

    # Consulta base de notificaciones
    notifications = Notification.objects.all().order_by("-created_at")

    # Aplicar filtros si están presentes
    if search_query:
        notifications = notifications.filter(title__icontains=search_query)

    if event_filter and event_filter != 'all':
        notifications = notifications.filter(event__id=event_filter)

    if priority_filter and priority_filter != 'all':
        notifications = notifications.filter(priority=priority_filter)

    return render(
        request,
        "app/notifications.html",
        {
            "notifications": notifications,
            "events": events,
            "has_notifications": notifications.exists(),
            "current_event_filter": event_filter,
            "current_priority_filter": priority_filter,
            "search_query": search_query,
            "user_is_organizer": request.user.is_organizer,
        },
    )

def notification_detail(request, id):

    # Verifica si el usuario es un organizador
    if not request.user.is_organizer:

        return redirect("home")

    notification = get_object_or_404(Notification, id=id)

    return render(
        request,
        "app/notification_detail.html",
        {
            "notification": notification,
        },
    )

@login_required

def notification_delete(request,id):
    user = request.user
    if not user.is_organizer:
        return redirect("notification")

    if request.method == "POST":
        notification = get_object_or_404(Notification, pk=id)
        notification.delete()
        return redirect("notification")

    return redirect("notification")

@login_required
def user_notifications(request):
# Obtener relaciones usuario-notificación (NotificationUser) del usuario actual,
# incluyendo los datos de la notificación asociada
    notification_users = NotificationUser.objects.filter(
        user=request.user
    ).select_related('notification').order_by("-notification__created_at")
    # Contar notificaciones no leídas
    unread_count = notification_users.filter(read=False).count()

    return render(
        request,
        "app/user_notifications.html",
        {
            "not_users": notification_users,
            "unread_count": unread_count,
            "has_notifications": notification_users.exists(),
        },
    )

def mark_notification_read(request, id=None):
    if request.method == "POST":
        try:
            # Buscar la relación NotificationUser por notification_id, no por id
            notif_user = NotificationUser.objects.get(id=id)
            notif_user.read = True
            notif_user.read_at = timezone.now()
            notif_user.save()
        except NotificationUser.DoesNotExist:
            messages.error(request, "No se encontró la notificación o no te pertenece.")
    return redirect("user_notifications")

# Marca todas las notificaciones del usuario como leídas
def mark_all_notifications_read(request):
    if request.method == "POST":
        NotificationUser.objects.filter(user=request.user, read=False).update(read=True, read_at=timezone.now())
    return redirect("user_notifications")


@login_required
def toggle_favorite(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    user = request.user
    favorite, created = Favorite.objects.get_or_create(user=user, event=event)

    if not created:
        favorite.delete()
        messages.success(request, "Evento eliminado de favoritos")
    else:
        messages.success(request, "Evento agregado a favoritos")

    referer = request.META.get('HTTP_REFERER', reverse('events'))

    return HttpResponseRedirect(referer)

def parse_survey_data(post_data):
    try:
        sat_lvl   = int(post_data['satisfaction_level'])
        ease      = int(post_data['ease_of_search'])
        pay_exp   = int(post_data['payment_experience'])
        received  = post_data.get('received_ticket') in ('on', 'true', '1')
        recommend = int(post_data['would_recommend'])
        comments  = post_data.get('additional_comments', '').strip()
    except (KeyError, ValueError) as e:
        raise ValueError("Datos de encuesta inválidos") from e

    return {
        'satisfaction_level': sat_lvl,
        'ease_of_search': ease,
        'payment_experience': pay_exp,
        'received_ticket': received,
        'would_recommend': recommend,
        'additional_comments': comments,
    }

@login_required
def satisfaction_survey(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    if SatisfactionSurvey.objects.filter(ticket=ticket).exists():
        return redirect('events')

    if request.method == 'POST':
        try:
            data = parse_survey_data(request.POST)
        except ValueError:
            return render(request, 'app/satisfaction_survey.html', {
                'ticket': ticket,
                'satisfaction_level_choices': SatisfactionSurvey._meta.get_field('satisfaction_level').choices,
                'ease_of_search_choices':    SatisfactionSurvey._meta.get_field('ease_of_search').choices,
                'payment_experience_choices':SatisfactionSurvey._meta.get_field('payment_experience').choices,
                'would_recommend_choices':   SatisfactionSurvey._meta.get_field('would_recommend').choices,
                'error_message': "Por favor, complete todos los campos correctamente."
            })

        SatisfactionSurvey.objects.create(ticket=ticket, **data)
        return redirect('events')

    # GET
    return render(request, 'app/satisfaction_survey.html', {
        'ticket': ticket,
        'satisfaction_level_choices': SatisfactionSurvey._meta.get_field('satisfaction_level').choices,
        'ease_of_search_choices':    SatisfactionSurvey._meta.get_field('ease_of_search').choices,
        'payment_experience_choices':SatisfactionSurvey._meta.get_field('payment_experience').choices,
        'would_recommend_choices':   SatisfactionSurvey._meta.get_field('would_recommend').choices,
    })
