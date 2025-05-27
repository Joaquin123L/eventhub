from django.urls import reverse
from app.test.test_e2e.base import BaseE2ETest
from app.models import User, Event, Ticket, SatisfactionSurvey
from django.utils import timezone
from datetime import timedelta


class SatisfactionSurveyE2ETest(BaseE2ETest):
    def setUp(self):
        super().setUp()
        self.organizer = User.objects.create_user(
            username="organizer",
            email="org@example.com",
            password="pass123",
            is_organizer=True,
        )
        self.user = User.objects.create_user(
            username="attendee",
            email="att@example.com",
            password="pass123",
            is_organizer=False,
        )
        self.event = Event.objects.create(
            title="Evento Público",
            description="Descripción",
            scheduled_at=timezone.now() + timedelta(days=1),
            organizer=self.organizer,
        )
        self.ticket = Ticket.objects.create(
            ticket_code="TCK123",
            quantity=1,
            user=self.user,
            event=self.event,
        )

    def _survey_url(self, ticket_id):
        path = reverse('satisfaction_survey', args=[ticket_id])
        return f"{self.live_server_url}{path}"

    def test_user_can_view_survey_form(self):
        """El usuario ve todos los campos de la encuesta"""
        self.login_user("attendee", "pass123")
        url = self._survey_url(self.ticket.pk)

        self.page.goto(url, wait_until='networkidle')
        self.page.wait_for_selector("h5:has-text('Encuesta de Satisfacción')", timeout=5000)

        form = self.page.locator("form")
        assert form.locator("select#satisfaction_level").is_visible()
        assert form.locator("select#ease_of_search").is_visible()
        assert form.locator("select#payment_experience").is_visible()
        assert form.locator("input#received_ticket[type=checkbox]").is_visible()
        assert form.locator("select#would_recommend").is_visible()
        assert form.locator("textarea#additional_comments").is_visible()
        assert form.locator("button[type=submit]", has_text="Enviar encuesta").is_visible()
        assert form.locator("a.btn-secondary", has_text="Omitir encuesta").is_visible()

    def test_user_can_submit_survey_and_redirect(self):
        """El usuario completa la encuesta y es redirigido a /events/"""
        self.login_user("attendee", "pass123")
        url = self._survey_url(self.ticket.pk)
        target = f"{self.live_server_url}{reverse('events')}"

        self.page.goto(url, wait_until='networkidle')
        self.page.wait_for_selector("form", timeout=5000)
        form = self.page.locator("form")

        form.locator("select#satisfaction_level").select_option("4")
        form.locator("select#ease_of_search").select_option("3")
        form.locator("select#payment_experience").select_option("5")
        form.locator("input#received_ticket").check()
        form.locator("select#would_recommend").select_option("2")
        form.locator("textarea#additional_comments").fill("¡Muy bueno!")

        form.locator("button[type=submit]", has_text="Enviar encuesta").click()
        self.page.wait_for_url(f"{target}**", timeout=5000)

        survey = SatisfactionSurvey.objects.get(ticket=self.ticket)
        assert survey.satisfaction_level == 4
        assert survey.ease_of_search == 3
        assert survey.payment_experience == 5
        assert survey.received_ticket is True
        assert survey.would_recommend == 2
        assert survey.additional_comments == "¡Muy bueno!"

    def test_error_shown_on_invalid_submission(self):
        """Si no completa los selects, aparece mensaje de error y sigue en la misma URL"""
        self.login_user("attendee", "pass123")
        url = self._survey_url(self.ticket.pk)

        self.page.goto(url, wait_until='networkidle')
        self.page.wait_for_selector("form", timeout=5000)
        form = self.page.locator("form")

        form.locator("button[type=submit]", has_text="Enviar encuesta").click()
        self.page.wait_for_selector("div.alert-danger", timeout=5000)

        alert = self.page.locator("div.alert-danger")
        assert alert.is_visible()
        assert "por favor" in alert.inner_text().lower()
        assert self.page.url.startswith(url)

    def test_skip_survey_button_redirects(self):
        """El enlace 'Omitir encuesta' lleva a /events/ sin crear encuesta"""
        self.login_user("attendee", "pass123")
        url = self._survey_url(self.ticket.pk)
        target = f"{self.live_server_url}{reverse('events')}"

        self.page.goto(url, wait_until='networkidle')
        self.page.wait_for_selector("form a.btn-secondary", timeout=5000)

        self.page.locator("form a.btn-secondary", has_text="Omitir encuesta").click()
        self.page.wait_for_url(f"{target}**", timeout=5000)

        assert not SatisfactionSurvey.objects.filter(ticket=self.ticket).exists()

    def test_cannot_access_after_submission(self):
        """Tras enviar, volver a la encuesta redirige a /events/"""
        self.login_user("attendee", "pass123")
        url = self._survey_url(self.ticket.pk)
        target = f"{self.live_server_url}{reverse('events')}"

        self.page.goto(url, wait_until='networkidle')
        self.page.wait_for_selector("form", timeout=5000)
        form = self.page.locator("form")
        form.locator("select#satisfaction_level").select_option("1")
        form.locator("select#ease_of_search").select_option("1")
        form.locator("select#payment_experience").select_option("1")
        form.locator("input#received_ticket").check()
        form.locator("select#would_recommend").select_option("1")
        form.locator("button[type=submit]", has_text="Enviar encuesta").click()
        self.page.wait_for_url(f"{target}**", timeout=5000)

        self.page.goto(url, wait_until='networkidle')
        self.page.wait_for_url(f"{target}**", timeout=5000)
