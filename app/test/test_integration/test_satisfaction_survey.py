from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from django.contrib.auth import get_user_model
from app.models import Event, Ticket, SatisfactionSurvey

User = get_user_model()


class SatisfactionSurveyIntegrationTest(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username="organizador",
            email="organizador@example.com",
            password="pass123",
        )
        self.user = User.objects.create_user(
            username="usuario",
            email="usuario@example.com",
            password="pass123",
        )
        self.event = Event.objects.create(
            title="Evento de prueba",
            description="Desc prueba",
            scheduled_at=timezone.now() + timedelta(days=1),
            organizer=self.organizer,
        )
        self.ticket = Ticket.objects.create(
            ticket_code="TCKT1",
            quantity=1,
            user=self.user,
            event=self.event,
        )

        self.client = Client()
        self.survey_url = reverse("satisfaction_survey", args=[self.ticket.id])


    def test_get_renders_form(self):
        """GET tras login devuelve 200 y muestra los campos de la encuesta"""
        self.client.login(username="usuario", password="pass123")
        resp = self.client.get(self.survey_url)
        self.assertEqual(resp.status_code, 200)

        content = resp.content.decode()
        for field_name in (
                'name="satisfaction_level"',
                'name="ease_of_search"',
                'name="payment_experience"',
                'name="received_ticket"',
                'name="would_recommend"',
        ):
            self.assertIn(field_name, content)

    def test_get_when_survey_exists_redirects(self):
        """Si ya hay encuesta para ese ticket, GET -> redirect eventos"""
        SatisfactionSurvey.objects.create(
            ticket=self.ticket,
            satisfaction_level=3,
            ease_of_search=3,
            payment_experience=3,
            received_ticket=True,
            would_recommend=3,
            additional_comments='',
        )
        self.client.login(username="usuario", password="pass123")
        resp = self.client.get(self.survey_url)
        self.assertRedirects(resp, reverse("events"))

    def test_post_valid_creates_survey_and_redirects(self):
        """POST válido crea encuesta y redirige a eventos"""
        self.client.login(username="usuario", password="pass123")
        data = {
            'satisfaction_level': '5',
            'ease_of_search': '4',
            'payment_experience': '2',
            'received_ticket': 'on',
            'would_recommend': '1',
            'additional_comments': '¡Excelente!',
        }
        resp = self.client.post(self.survey_url, data, follow=True)
        self.assertRedirects(resp, reverse("events"))
        survey = SatisfactionSurvey.objects.get(ticket=self.ticket)
        self.assertEqual(survey.satisfaction_level, 5)
        self.assertEqual(survey.ease_of_search, 4)
        self.assertEqual(survey.payment_experience, 2)
        self.assertTrue(survey.received_ticket)
        self.assertEqual(survey.would_recommend, 1)
        self.assertEqual(survey.additional_comments, '¡Excelente!')

    def test_post_invalid_data_renders_error(self):
        """POST con datos inválidos vuelve a renderizar con mensaje de error"""
        self.client.login(username="usuario", password="pass123")
        data = {
            'satisfaction_level': 'no_int',
        }
        resp = self.client.post(self.survey_url, data)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode().lower()
        self.assertIn("por favor", content)
        self.assertFalse(SatisfactionSurvey.objects.filter(ticket=self.ticket).exists())

    def test_nonexistent_ticket_returns_404(self):
        """GET a ticket inexistente devuelve 404"""
        self.client.login(username="usuario", password="pass123")
        bad_url = reverse("satisfaction_survey", args=[9999])
        resp = self.client.get(bad_url)
        self.assertEqual(resp.status_code, 404)

        resp2 = self.client.post(bad_url, {})
        self.assertEqual(resp2.status_code, 404)
