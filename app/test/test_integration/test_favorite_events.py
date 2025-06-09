import datetime

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from app.models import Event, Favorite, User


class ToggleFavoriteIntegrationTest(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username="organizador",
            email="organizador@example.com",
            password="password123",
            is_organizer=True,
        )

        self.user = User.objects.create_user(
            username="usuario",
            email="usuario@example.com",
            password="password123",
            is_organizer=False,
        )

        self.event = Event.objects.create(
            title="Evento de prueba",
            description="Descripción del evento",
            scheduled_at=timezone.now() + datetime.timedelta(days=1),
            organizer=self.organizer,
        )

        self.client = Client()
        self.client.login(username="usuario", password="password123")

        self.toggle_url = reverse("toggle_favorite", args=[self.event.pk])

    def test_add_event_to_favorite(self):
        """Verifica que se pueda agregar un evento a favoritos"""
        response = self.client.get(self.toggle_url)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Favorite.objects.filter(user=self.user, event=self.event).exists())

    def test_remove_event_to_favorite(self):
        """Verifica que se pueda quitar un evento previamente agregado a favoritos"""
        Favorite.objects.create(user=self.user, event=self.event)

        response = self.client.get(self.toggle_url)
        self.assertEqual(response.status_code, 302)

        self.assertFalse(Favorite.objects.filter(user=self.user, event=self.event).exists())

    def test_favorite_is_not_duplicated_on_multiple_toggles(self):
        """Verifica que no se cree más de un registro de favorito por usuario-evento"""
        self.client.get(self.toggle_url)
        self.client.get(self.toggle_url)
        self.client.get(self.toggle_url)

        favoritos = Favorite.objects.filter(user=self.user, event=self.event)
        self.assertEqual(favoritos.count(), 1)

    def test_favorite_remains_user_specific(self):
        """Verifica que el favorito es individual por usuario"""
        otro_user = User.objects.create_user(
            username="otro",
            email="otro@example.com",
            password="password123",
        )

        self.client.get(self.toggle_url)
        self.assertTrue(Favorite.objects.filter(user=self.user, event=self.event).exists())

        self.client.logout()
        self.client.login(username="otro", password="password123")
        self.assertFalse(Favorite.objects.filter(user=otro_user, event=self.event).exists())

        self.client.get(reverse("toggle_favorite", args=[self.event.pk]))
        self.assertTrue(Favorite.objects.filter(user=otro_user, event=self.event).exists())

    def test_redirects_to_default_if_no_referer(self):
        """Verifica que se redirige a 'events' si no hay HTTP_REFERER"""
        response = self.client.get(self.toggle_url)
        self.assertRedirects(response, reverse("events"))
