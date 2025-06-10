import datetime
import re
import unittest

from django.utils import timezone
from playwright.sync_api import expect

from app.models import Category, Event, User, Venue
from app.test.test_e2e.base import BaseE2ETest


class EventBaseTest(BaseE2ETest):
    """Clase base específica para tests de eventos"""

    def setUp(self):
        super().setUp()

        self.category = Category.objects.create(name="Conferencia", is_active=True)
        self.venue = Venue.objects.create(name="Auditorio Principal", capacity=100)

        # Crear usuario organizador
        self.organizer = User.objects.create_user(
            username="organizador",
            email="organizador@example.com",
            password="password123",
            is_organizer=True,
        )

        # Crear usuario regular
        self.regular_user = User.objects.create_user(
            username="usuario",
            email="usuario@example.com",
            password="password123",
            is_organizer=False,
        )

        # Crear eventos de prueba
        # Evento 1
        event_date1 = timezone.make_aware(datetime.datetime(2026, 2, 10, 10, 10))
        self.event1 = Event.objects.create(
            title="Evento de prueba 1",
            description="Descripción del evento 1",
            scheduled_at=event_date1,
            organizer=self.organizer,
            category=self.category,  # Añadir
            venue=self.venue,        # Añadir
            capacity=50,
        )

        # Evento 2
        event_date2 = timezone.make_aware(datetime.datetime(2026, 3, 15, 14, 30))
        self.event2 = Event.objects.create(
            title="Evento de prueba 2",
            description="Descripción del evento 2",
            scheduled_at=event_date2,
            organizer=self.organizer,
        )

    def _table_has_event_info(self):
        """Método auxiliar para verificar que la tabla tiene la información correcta de eventos"""
        # Verificar encabezados de la tabla
        self.page.wait_for_selector("table", timeout=10000)

        headers = self.page.locator("table thead th")
        expect(headers).to_have_count(7)

        # Verificar cada encabezado en el orden correcto
        expect(headers.nth(0)).to_have_text("Título")
        expect(headers.nth(1)).to_have_text("Descripción")
        expect(headers.nth(2)).to_have_text("Fecha")
        expect(headers.nth(3)).to_have_text("Categoría")
        expect(headers.nth(4)).to_have_text("Locación")
        expect(headers.nth(5)).to_have_text("Estado")
        expect(headers.nth(6)).to_have_text("Acciones")

        # Verificar que los eventos aparecen en la tabla
        rows = self.page.locator("table tbody tr")
        expect(rows).to_have_count(2)

        # Verificar datos del primer evento
        row0 = rows.nth(0)
        expect(row0.locator("td").nth(0)).to_have_text("Evento de prueba 1")
        expect(row0.locator("td").nth(1)).to_have_text("Descripción del evento 1")
        expect(row0.locator("td").nth(2)).to_have_text("10 feb 2026, 10:10")

        # Verificar datos del segundo evento
        expect(rows.nth(1).locator("td").nth(0)).to_have_text("Evento de prueba 2")
        expect(rows.nth(1).locator("td").nth(1)).to_have_text("Descripción del evento 2")
        expect(rows.nth(1).locator("td").nth(2)).to_have_text("15 mar 2026, 14:30")

    @unittest.skip("Método auxiliar, no es un test")
    def _table_has_correct_actions(self, user_type):
        """Método auxiliar para verificar que las acciones son correctas según el tipo de usuario"""
        row0 = self.page.locator("table tbody tr").nth(0)

        # El botón "Ver Detalle" ahora es solo un ícono (bi-eye)
        detail_button = row0.locator("a").filter(has=self.page.locator("i.bi-eye")).first
        expect(detail_button).to_be_visible()
        expect(detail_button).to_have_attribute("href", f"/events/{self.event1.pk}/")

        if user_type == "organizador":
            # Botón de editar (ícono bi-pencil)
            edit_button = row0.locator("a").filter(has=self.page.locator("i.bi-pencil")).first
            expect(edit_button).to_be_visible()
            expect(edit_button).to_have_attribute("href", f"/events/{self.event1.pk}/edit/")

            # Botón de tickets (ícono bi-ticket)
            tickets_button = row0.locator("a").filter(has=self.page.locator("i.bi-ticket")).first
            expect(tickets_button).to_be_visible()
            expect(tickets_button).to_have_attribute("href", f"/events/{self.event1.pk}/tickets/")

            # Formulario de eliminar
            delete_form = row0.locator("form").filter(has_text="").first
            expect(delete_form).to_have_attribute("action", f"/events/{self.event1.pk}/delete/")
            expect(delete_form).to_have_attribute("method", "POST")

            # Botón eliminar (ícono bi-trash)
            delete_button = delete_form.locator("button").filter(has=self.page.locator("i.bi-trash"))
            expect(delete_button).to_be_visible()

            # Formulario de cancelar
            cancel_form = row0.locator("form").nth(1)  # Segundo formulario
            expect(cancel_form).to_have_attribute("action", f"/events/{self.event1.pk}/cancel/")
            expect(cancel_form).to_have_attribute("method", "POST")

            # Botón cancelar (ícono bi-x-circle)
            cancel_button = cancel_form.locator("button").filter(has=self.page.locator("i.bi-x-circle"))
            expect(cancel_button).to_be_visible()

        else:
            # Para usuarios regulares, solo debe existir el botón de ver detalle
            edit_button = row0.locator("a").filter(has=self.page.locator("i.bi-pencil"))
            tickets_button = row0.locator("a").filter(has=self.page.locator("i.bi-ticket"))
            delete_forms = row0.locator("form")

            expect(edit_button).to_have_count(0)
            expect(tickets_button).to_have_count(0)
            expect(delete_forms).to_have_count(0)

class EventAuthenticationTest(EventBaseTest):
    """Tests relacionados con la autenticación y permisos de usuarios en eventos"""

    def test_events_page_requires_login(self):
        """Test que verifica que la página de eventos requiere inicio de sesión"""
        # Cerrar sesión si hay alguna activa
        self.context.clear_cookies()

        # Intentar ir a la página de eventos sin iniciar sesión
        self.page.goto(f"{self.live_server_url}/events/")

        # Verificar que redirige a la página de login
        expect(self.page).to_have_url(re.compile(r"/accounts/login/"))


class EventDisplayTest(EventBaseTest):
    """Tests relacionados con la visualización de la página de eventos"""

    def test_events_page_display_as_organizer(self):
        """Test que verifica la visualización correcta de la página de eventos para organizadores"""
        self.login_user("organizador", "password123")
        self.page.goto(f"{self.live_server_url}/events/")

        # Verificar el título de la página
        expect(self.page).to_have_title("Eventos")

        # Verificar que existe un encabezado con el texto "Eventos"
        header = self.page.locator("h1")
        expect(header).to_have_text("Eventos")
        expect(header).to_be_visible()

        # Verificar que existe una tabla
        table = self.page.locator("table")
        expect(table).to_be_visible()

        self._table_has_event_info()
        self._table_has_correct_actions("organizador")

    def test_events_page_regular_user(self):
        """Test que verifica la visualización de la página de eventos para un usuario regular"""
        # Iniciar sesión como usuario regular
        self.login_user("usuario", "password123")

        # Ir a la página de eventos
        self.page.goto(f"{self.live_server_url}/events/")

        expect(self.page).to_have_title("Eventos")

        # Verificar que existe un encabezado con el texto "Eventos"
        header = self.page.locator("h1")
        expect(header).to_have_text("Eventos")
        expect(header).to_be_visible()

        # Verificar que existe una tabla
        table = self.page.locator("table")
        expect(table).to_be_visible()

        self._table_has_event_info()
        self._table_has_correct_actions("regular")

    def test_events_page_no_events(self):
        """Test que verifica el comportamiento cuando no hay eventos"""
        # Eliminar todos los eventos
        Event.objects.all().delete()

        self.login_user("organizador", "password123")

        # Ir a la página de eventos
        self.page.goto(f"{self.live_server_url}/events/")

        # Verificar que existe un mensaje indicando que no hay eventos
        no_events_message = self.page.locator("text=No hay eventos disponibles")
        expect(no_events_message).to_be_visible()




class EventPermissionsTest(EventBaseTest):
    """Tests relacionados con los permisos de usuario para diferentes funcionalidades"""

    def test_buttons_visible_only_for_organizer(self):
        """Test que verifica que los botones de gestión solo son visibles para organizadores"""
        # Primero verificar como organizador
        self.login_user("organizador", "password123")
        self.page.goto(f"{self.live_server_url}/events/")

        # Verificar que existe el botón de crear
        create_button = self.page.get_by_role("link", name="Crear Evento")
        expect(create_button).to_be_visible()

        # Cerrar sesión
        self.page.get_by_role("button", name="Salir").click()

        # Iniciar sesión como usuario regular
        self.login_user("usuario", "password123")
        self.page.goto(f"{self.live_server_url}/events/")

        # Verificar que NO existe el botón de crear
        create_button = self.page.get_by_role("link", name="Crear Evento")
        expect(create_button).to_have_count(0)

    #test que verifica que la alerta de demanda solo sea visible para organizadores
    def test_demand_label_visible_only_for_organizer(self):
        self.event100 = Event.objects.create(
        title="Evento con alta demanda",
        description="Evento de prueba",
        scheduled_at=timezone.now() + datetime.timedelta(days=1),
        capacity=100,
        organizer=self.organizer
    )
        # Loguearse como organizador
        self.login_user("organizador", "password123")
        self.page.goto(f"{self.live_server_url}/events/{self.event100.pk}/")

        # Verificar que aparece el mensaje de DEMANDA ALTA
        expect(self.page.get_by_text("DEMANDA BAJA")).to_be_visible()

        # Cerrar sesión
        self.page.get_by_role("button", name="Salir").click()

        # Loguearse como usuario común
        self.login_user("usuario", "password123")
        self.page.goto(f"{self.live_server_url}/events/{self.event1.pk}/")

        # Verificar que NO aparece el mensaje de DEMANDA ALTA
        expect(self.page.get_by_text("DEMANDA BAJA")).to_have_count(0)

    def test_event_verificate_countdown(self):
        """Test que verifica que el contador de eventos se muestre correctamente para usuarios que no son organizadores"""
        # Iniciar sesión como usuario regular
        self.login_user("usuario", "password123")

        # Ir a la página de eventos
        self.page.goto(f"{self.live_server_url}/events/{self.event1.pk}/")

        # Verificar que el evento tiene un contador visible
        countdown = self.page.locator("#countdown")
        expect(countdown).to_be_visible()

#verifica que si sos organizador no se muestre el contador
    def test_event_no_countdown_for_organizer(self):
        """Test que verifica que el contador de eventos no se muestre para organizadores"""
        # Iniciar sesión como organizador
        self.login_user("organizador", "password123")

        # Ir a la página de eventos
        self.page.goto(f"{self.live_server_url}/events/{self.event1.pk}/")

        # Verificar que el evento no tiene un contador visible
        countdown = self.page.locator("#countdown")
        expect(countdown).to_have_count(0)

    def test_filter_past_events_visible_only_for_organizer(self):
        """Test que verifica que el filtro de eventos pasados solo es visible para organizadores"""

    # Iniciar sesión como organizador
        self.login_user("organizador", "password123")
        self.page.goto(f"{self.live_server_url}/events/")

    # Verificar que el checkbox 'Ver eventos pasados' es visible
        past_events_checkbox = self.page.get_by_label("Ver eventos pasados")
        expect(past_events_checkbox).to_be_visible()

    # Cerrar sesión
        self.page.get_by_role("button", name="Salir").click()

    # Iniciar sesión como usuario regular
        self.login_user("usuario", "password123")
        self.page.goto(f"{self.live_server_url}/events/")

    # Verificar que el checkbox 'Ver eventos pasados' no esté presente
        past_events_checkbox = self.page.locator("label", has_text="Ver eventos pasados")

class EventCRUDTest(EventBaseTest):
    """Tests relacionados con las operaciones CRUD (Crear, Leer, Actualizar, Eliminar) de eventos"""

    def test_create_new_event_organizer(self):
        """Test que verifica la funcionalidad de crear un nuevo evento para organizadores"""
        # Iniciar sesión como organizador
        self.login_user("organizador", "password123")

        # Ir a la página de eventos
        self.page.goto(f"{self.live_server_url}/events/")

        # Hacer clic en el botón de crear evento
        self.page.get_by_role("link", name="Crear Evento").click()

        # Verificar que estamos en la página de creación de evento
        expect(self.page).to_have_url(f"{self.live_server_url}/events/create/")

        header = self.page.locator("h1")
        expect(header).to_have_text("Crear evento")
        expect(header).to_be_visible()

        # Completar el formulario
        self.page.get_by_label("Título del Evento").fill("Evento de prueba E2E")
        self.page.get_by_label("Descripción").fill("Descripción creada desde prueba E2E")
        self.page.get_by_label("Fecha").fill("2027-06-15")
        self.page.get_by_label("Hora").fill("16:45")
        self.page.get_by_label("Categoría").select_option(str(self.category.pk))
        self.page.get_by_label("Locación").select_option(str(self.venue.pk))
        self.page.get_by_label("Capacidad").fill("50")

        # Enviar el formulario
        self.page.get_by_role("button", name="Crear Evento").click()

        # Verificar que redirigió a la página de eventos
        expect(self.page).to_have_url(f"{self.live_server_url}/events/")

        # Verificar que ahora hay 3 eventos
        rows = self.page.locator("table tbody tr")
        expect(rows).to_have_count(3)

        row = self.page.locator("table tbody tr").last
        expect(row.locator("td").nth(0)).to_have_text("Evento de prueba E2E")
        expect(row.locator("td").nth(1)).to_have_text("Descripción creada desde prueba E2E")
        expect(row.locator("td").nth(2)).to_have_text("15 jun 2027, 16:45")

    def test_edit_event_organizer(self):
        """Test que verifica la funcionalidad de editar un evento para organizadores"""
        # Iniciar sesión como organizador
        self.login_user("organizador", "password123")

        # Ir a la página de eventos
        self.page.goto(f"{self.live_server_url}/events/")

        # Hacer clic en el botón editar del primer evento
        self.page.locator("a.btn-outline-secondary").first.click()

        # Verificar que estamos en la página de edición
        expect(self.page).to_have_url(f"{self.live_server_url}/events/{self.event1.pk}/edit/")

        header = self.page.locator("h1")
        expect(header).to_have_text("Editar evento")
        expect(header).to_be_visible()

        # Verificar que el formulario está precargado con los datos del evento y luego los editamos
        title = self.page.get_by_label("Título del Evento")
        expect(title).to_have_value("Evento de prueba 1")
        title.fill("Titulo editado")

        description = self.page.get_by_label("Descripción")
        expect(description).to_have_value("Descripción del evento 1")
        description.fill("Descripcion Editada")

        date = self.page.get_by_label("Fecha")
        expect(date).to_have_value("2026-02-10")
        date.fill("2026-02-11")

        time = self.page.get_by_label("Hora")
        expect(time).to_have_value("10:10")
        time.fill("03:00")

        category_select = self.page.get_by_label("Categoría")
        expect(category_select).to_have_value(str(self.category.pk))

        venue_select = self.page.get_by_label("Locación")
        expect(venue_select).to_have_value(str(self.venue.pk))

        capacity_input = self.page.get_by_label("Capacidad")
        expect(capacity_input).to_have_value("50")
        capacity_input.fill("75")

        # Enviar el formulario
        self.page.get_by_role("button", name="Guardar Cambios").click()

        # Verificar que redirigió a la página de eventos
        expect(self.page).to_have_url(f"{self.live_server_url}/events/")

        # Verificar que el título del evento ha sido actualizado
        row = self.page.locator("table tbody tr").first
        expect(row.locator("td").nth(0)).to_have_text("Titulo editado")
        expect(row.locator("td").nth(1)).to_have_text("Descripcion Editada")
        expect(row.locator("td").nth(2)).to_have_text("11 feb 2026, 03:00")

    def test_delete_event_organizer(self):
        """Test que verifica la funcionalidad de eliminar un evento para organizadores"""
        # Iniciar sesión como organizador
        self.login_user("organizador", "password123")

        # Ir a la página de eventos
        self.page.goto(f"{self.live_server_url}/events/")

        # Contar eventos antes de eliminar
        initial_count = len(self.page.locator("table tbody tr").all())

        # Hacer clic en el botón eliminar del primer evento
        self.page.locator("button.btn-outline-danger").first.click()

        # Verificar que redirigió a la página de eventos
        expect(self.page).to_have_url(f"{self.live_server_url}/events/")

        # Verificar que ahora hay un evento menos
        rows = self.page.locator("table tbody tr")
        expect(rows).to_have_count(initial_count - 1)

        # Verificar que el evento eliminado ya no aparece en la tabla
        expect(self.page.get_by_text("Evento de prueba 1")).to_have_count(0)

class EventStateFlowE2ETest(EventBaseTest):

    def test_complete_event_state_flow(self):


        self.event1.capacity = 2
        self.event1.save()
        # 1. Verificar estado inicial (Activo)
        self.login_user("usuario", "password123")

        self.page.goto(f"{self.live_server_url}/events/", wait_until="networkidle")
        fila_correcta = self.page.locator("table tbody tr", has_text="Evento de prueba 1").first
        expect(fila_correcta.locator("td").nth(5)).to_have_text("Activo")

        print("Paso 1: Evento creado con estado Activo - OK")

        self.page.goto(f"{self.live_server_url}/ticket_compra/{self.event1.pk}", wait_until="networkidle")

        # Llenar datos del formulario
        self.page.fill("input[name='card_name']", "Juan Pérez")
        self.page.fill("input[name='card_number']", "4242424242424242")
        self.page.fill("input[name='card_expiry']", "12/30")
        self.page.fill("input[name='card_cvv']", "123")
        self.page.check("input[name='accept_terms']")
        self.page.select_option("select[name='type']", "general")
        self.page.fill("#quantity", "1")

        # Enviar formulario
        with self.page.expect_navigation(wait_until="networkidle"):
            self.page.click("#submit-btn")


        # Verificar que el estado sigue siendo Activo (aún hay capacidad)
        self.page.goto(f"{self.live_server_url}/events/")
        fila_correcta = self.page.locator("table tbody tr", has_text="Evento de prueba 1").first
        expect(fila_correcta.locator("td").nth(5)).to_have_text("Activo")
        print("Paso 2: El evento sigue en estado Activo - OK")

        self.page.goto(f"{self.live_server_url}/ticket_compra/{self.event1.pk}", wait_until="networkidle")

        # Llenar datos del formulario
        self.page.fill("input[name='card_name']", "Juan Pérez")
        self.page.fill("input[name='card_number']", "4242424242424242")
        self.page.fill("input[name='card_expiry']", "12/30")
        self.page.fill("input[name='card_cvv']", "123")
        self.page.check("input[name='accept_terms']")
        self.page.select_option("select[name='type']", "general")
        self.page.fill("#quantity", "1")

        with self.page.expect_navigation(wait_until="networkidle"):
            self.page.click("#submit-btn")

        self.page.goto(f"{self.live_server_url}/events/")
        fila_correcta = self.page.locator("table tbody tr", has_text="Evento de prueba 1").first
        expect(fila_correcta.locator("td").nth(5)).to_have_text("Agotado")
        print("Paso 3: El evento Se Agoto - OK")

        # Navegar a la lista de tickets
        self.page.goto(f"{self.live_server_url}/Mis_tickets/", wait_until="networkidle")

        # Hacer clic en el botón de eliminar del primer ticket
        fila = self.page.locator("tr", has_text="Evento de prueba 1").first
        fila.locator("form[action*='ticket_delete'] button[type='submit']").click()
        self.page.wait_for_load_state("networkidle")
        self.page.goto(f"{self.live_server_url}/events/")
        fila_correcta = self.page.locator("table tbody tr", has_text="Evento de prueba 1").first
        expect(fila_correcta.locator("td").nth(5)).to_have_text("Activo")
        print("Paso 4: El evento volvio al estado Activo - OK")

    def test_complete_event_state_Cancelar(self):
        self.login_user("organizador", "password123")
        #Se corrobora que el evento existe y esta activo
        self.page.goto(f"{self.live_server_url}/events/?category=&venue=&order=asc&ver_pasados=on/", wait_until="networkidle")
        fila_correcta = self.page.locator("table tbody tr", has_text="Evento de prueba 1").first
        expect(fila_correcta.locator("td").nth(5)).to_have_text("Activo")

        print("Paso 1: Evento esta Activo - OK")
        #Buscamos el evento 1 y lo cancelamos
        fila_evento = self.page.locator("table tbody tr", has_text="Evento de prueba 1").first
        cancel_button = fila_evento.locator("form[action*='/cancel/'] button[type='submit']")
        cancel_button.click()
        #mostramos eventos pasados para ver el cancelado
        self.page.locator("input#ver_pasados").check()
        self.page.wait_for_load_state("networkidle")

        #revisamos si el evento 1 esta cancelado
        fila_evento = self.page.locator("table tbody tr", has_text="Evento de prueba 1").first
        estado_td = fila_evento.locator("td").nth(5)
        expect(estado_td).to_have_text("Cancelado")
        print("Paso 2: Evento esta Cancelado - OK")

