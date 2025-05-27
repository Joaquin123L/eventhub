from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from app.models import Event, Ticket, SatisfactionSurvey

from datetime import timedelta

User = get_user_model()


class SatisfactionSurveyViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpass123',
        )
        self.event = Event.objects.create(
            title="Evento de prueba",
            description="Descripción del evento",
            scheduled_at=timezone.now() + timedelta(days=1),
            organizer=self.user,
        )
        self.ticket = Ticket.objects.create(
            ticket_code='ABC123',
            quantity=1,
            user=self.user,
            event=self.event,
        )
        self.url = reverse('satisfaction_survey', args=[self.ticket.pk])
        self.login = self.client.login(username='testuser', password='testpass123')

    def test_requires_login(self):
        """Sin login, debe redirect a login?next=..."""
        self.client.logout()
        resp = self.client.get(self.url)
        login_url = reverse('login')
        self.assertRedirects(resp, f'{login_url}?next={self.url}')

    def test_get_renders_form_context(self):
        """GET inicial muestra el formulario con los choices y el ticket en contexto"""
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        ctx = resp.context
        self.assertIn('satisfaction_level_choices', ctx)
        self.assertIn('ease_of_search_choices', ctx)
        self.assertIn('payment_experience_choices', ctx)
        self.assertIn('would_recommend_choices', ctx)
        self.assertEqual(ctx['ticket'], self.ticket)

    def test_get_when_survey_exists_redirects(self):
        """Si ya existe una encuesta para el ticket, redirige a 'events'"""
        SatisfactionSurvey.objects.create(
            ticket=self.ticket,
            satisfaction_level=3,
            ease_of_search=3,
            payment_experience=3,
            received_ticket=True,
            would_recommend=3,
            additional_comments='',
        )
        resp = self.client.get(self.url, follow=True)
        self.assertRedirects(resp, reverse('events'))

    def test_post_creates_survey_and_redirects(self):
        """POST con datos válidos crea la encuesta y redirige a 'events'"""
        data = {
            'satisfaction_level': '5',
            'ease_of_search': '4',
            'payment_experience': '2',
            'received_ticket': 'on',
            'would_recommend': '1',
            'additional_comments': '¡Muy buena!',
        }
        resp = self.client.post(self.url, data, follow=True)
        self.assertRedirects(resp, reverse('events'))
        survey_qs = SatisfactionSurvey.objects.filter(ticket=self.ticket)
        self.assertTrue(survey_qs.exists())
        survey = survey_qs.get()
        self.assertEqual(survey.satisfaction_level, 5)
        self.assertEqual(survey.ease_of_search, 4)
        self.assertEqual(survey.payment_experience, 2)
        self.assertTrue(survey.received_ticket)
        self.assertEqual(survey.would_recommend, 1)
        self.assertEqual(survey.additional_comments, '¡Muy buena!')

    def test_post_with_false_received_ticket(self):
        """POST con received_ticket ausente produce False en el campo"""
        data = {
            'satisfaction_level': '3',
            'ease_of_search': '3',
            'payment_experience': '3',
            'would_recommend': '4',
            'additional_comments': '',
        }
        self.client.post(self.url, data)
        survey = SatisfactionSurvey.objects.get(ticket=self.ticket)
        self.assertFalse(survey.received_ticket)

    def test_post_invalid_missing_fields_renders_error(self):
        """POST con campo faltante o no entero renderiza el template con mensaje de error"""
        data = {
            'satisfaction_level': '',
            'ease_of_search': 'x',
        }
        resp = self.client.post(self.url, data)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'app/satisfaction_survey.html')
        self.assertIn('error_message', resp.context)
        self.assertIn('Por favor', resp.context['error_message'])

    def test_nonexistent_ticket_returns_404(self):
        """Acceder a un ticket que no existe devuelve 404"""
        url = reverse('satisfaction_survey', args=[9999])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)
