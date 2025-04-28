import datetime
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.db.models import Count
from django.http import HttpResponseForbidden
from .models import Event, User, Category, Comment, Venue, Ticket, Rating
from django.contrib import messages
import re
import random
from django.db import IntegrityError


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
def events(request):
    #si el usuario es organizador recupera todos sus eventos, si el usuario no es organizador recupera todos los eventos siempre y cuando la fecha del evento sea posterior a la actual. De esta forma permitimos que el usuario que no es  organizador pueda comprar entradas.
    if request.user.is_organizer:
        events = Event.objects.filter(organizer=request.user).order_by("scheduled_at")
    else:
        events = Event.objects.filter(scheduled_at__gte=timezone.now()).order_by("scheduled_at")
    return render(
        request,
        "app/events.html",
        {"events": events, "user_is_organizer": request.user.is_organizer},
    )


@login_required
def event_detail(request, id):
    event = get_object_or_404(Event, pk=id)
    todos_los_comentarios = Comment.objects.filter(event=event).order_by('-created_at')
    ratings = Rating.objects.filter(event=event).order_by('-created_at')


    return render(request, "app/event_detail.html", {"event": event, "todos_los_comentarios": todos_los_comentarios,
        "user_is_organizer": request.user.is_organizer,})
    return render(request, "app/event_detail.html", {"event": event, "todos_los_comentarios": todos_los_comentarios, "ratings": ratings, "user_is_organizer": request.user.is_organizer})



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

        [year, month, day] = date.split("-")
        [hour, minutes] = time.split(":")

        scheduled_at = timezone.make_aware(
            datetime.datetime(int(year), int(month), int(day), int(hour), int(minutes))
        )

        category = get_object_or_404(Category, pk=category_id)
        venue = get_object_or_404(Venue, pk=venue_id)

        if id is None:
            success, errors = Event.new(title, description, scheduled_at, request.user, category, venue)
        else:
            event = get_object_or_404(Event, pk=id)
            event.update(title, description, scheduled_at, request.user, category, venue)

        return redirect("events")

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
            messages.error(request, "No se puede eliminar esta categoría porque tiene eventos asociados.")
        
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
    
    if request.method == 'POST':
        # Obtener datos del formulario
        ticket_code = request.POST.get('ticket_code')
        quantity = request.POST.get('quantity')
        type_entrada = request.POST.get('type')
        try:
            quantity = int(quantity)
        except ValueError:
            quantity = 0 
        
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
        
        messages.success(request, f"¡Compra exitosa! Tu código de ticket es: {ticket_code}")
        return redirect('events')
    return render(request, 'app/ticket_compra.html', {
        'event': event, 
        'event_id': event_id
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
    
    # Simular un 95% de probabilidad de éxito en el pago
    return random.random() < 0.95

@login_required
def ticket_delete(request,event_id, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    event_id=event_id

    if request.method == 'POST':
        ticket.delete()
        messages.success(request, "Ticket eliminado correctamente")
        return redirect('tickets', event_id=event_id)

    return render(request, 'app/tickets', {'ticket': ticket})

@login_required
def mis_tickets(request):
    tickets = Ticket.objects.filter(user=request.user).order_by('-buy_date')
    return render(request, 'app/mis_tickets.html', {'tickets': tickets})

def rating_create(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    #debo validar que el usuario no califique el mismo evento mas de una vez
    if Rating.objects.filter(user=request.user, event=event).exists():
        messages.error(request, "Ya has calificado este evento")
        return redirect('event_detail', id=event_id)
    
    # debo implementar cuando exista el modelo Ticket que solo se pueda hacer una reseña si el usuario tiene un ticket para el evento

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
