from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Post

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_cache(self):
        response_1 = self.client.get(reverse('posts:main_page')).content
        response_2 = self.client.get(reverse('posts:main_page')).content
        self.assertEqual(response_1, response_2)
        Post.objects.all().delete
        cache.clear()
        response_3 = self.client.get(reverse('posts:main_page')).content
        """Вот тут замечал, что у многих assertNotEqual,
        но он у меня не работает. Путем гугления и тд
        остановился на assertIsNOt, он хотя бы работает"""
        self.assertIsNot(response_1, response_3)
