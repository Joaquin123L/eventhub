from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from app.models import Event, Favorite

from datetime import timedelta

User = get_user_model()


class ToggleFavoriteViewTest(TestCase):
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

        self.toggle_url = reverse('toggle_favorite', args=[self.event.id])

    def test_toggle_favorite_adds_event(self):
        """Test que verifica que un evento se agrega a favoritos correctamente"""
        self.client.login(username='testuser', password='testpass123')

        response = self.client.get(self.toggle_url, follow=True)

        self.assertRedirects(response, reverse('events'))
        self.assertTrue(Favorite.objects.filter(user=self.user, event=self.event).exists())

    def test_toggle_favorite_removes_event(self):
        """Test que verifica que un evento ya marcado como favorito se elimina al hacer toggle"""
        self.client.login(username='testuser', password='testpass123')

        Favorite.objects.create(user=self.user, event=self.event)

        response = self.client.get(self.toggle_url, follow=True)

        self.assertRedirects(response, reverse('events'))
        self.assertFalse(Favorite.objects.filter(user=self.user, event=self.event).exists())

    def test_toggle_favorite_redirects_to_referer(self):
        """Test que verifica que la vista redirige a la URL de origen (Referer)"""
        self.client.login(username='testuser', password='testpass123')

        referer_url = reverse('event_detail', args=[self.event.id])
        response = self.client.get(self.toggle_url, HTTP_REFERER=referer_url)

        self.assertRedirects(response, referer_url)

    def test_toggle_favorite_requires_login(self):
        """Test que verifica que la vista requiere autenticación"""
        response = self.client.get(self.toggle_url)
        login_url = reverse('login')
        self.assertRedirects(response, f'{login_url}?next={self.toggle_url}')

    def test_toggle_favorite_twice_results_in_no_favorite(self):
        """Test que verifica que hacer toggle dos veces deja el evento sin marcar como favorito"""
        self.client.login(username='testuser', password='testpass123')

        self.client.get(self.toggle_url)
        self.assertTrue(Favorite.objects.filter(user=self.user, event=self.event).exists())

        self.client.get(self.toggle_url)
        self.assertFalse(Favorite.objects.filter(user=self.user, event=self.event).exists())

    def test_favorite_created_once(self):
        """Test que verifica que no se crean duplicados de favoritos"""
        self.client.login(username='testuser', password='testpass123')

        self.client.get(self.toggle_url)
        self.client.get(self.toggle_url)
        self.client.get(self.toggle_url)

        self.assertEqual(Favorite.objects.filter(user=self.user, event=self.event).count(), 1)

    def test_toggle_favorite_nonexistent_event_returns_404(self):
        """Test que verifica que acceder a un ID de evento inexistente devuelve 404"""
        self.client.login(username='testuser', password='testpass123')

        url = reverse('toggle_favorite', args=[9999])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_toggle_favorite_different_user(self):
        """Test que verifica que distintos usuarios pueden marcar o desmarcar favoritos independientemente"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123',
        )

        self.client.login(username='otheruser', password='otherpass123')
        self.client.get(self.toggle_url)

        self.assertTrue(Favorite.objects.filter(user=other_user, event=self.event).exists())
        self.assertFalse(Favorite.objects.filter(user=self.user, event=self.event).exists())

    def test_toggle_favorite_message_added(self):
        """Test que verifica que se añaden los mensajes correspondientes al agregar o eliminar"""
        self.client.login(username='testuser', password='testpass123')

        response = self.client.get(self.toggle_url, follow=True)
        messages = list(response.context["messages"])
        self.assertTrue(any("agregado" in msg.message.lower() for msg in messages))

        response = self.client.get(self.toggle_url, follow=True)
        messages = list(response.context["messages"])
        self.assertTrue(any("eliminado" in msg.message.lower() for msg in messages))
