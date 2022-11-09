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
        cache.clear()
        self.guest_client = Client()
        self.client = Client()
        self.client.force_login(self.user)

    def test_cache(self):
        initial_response = self.guest_client.get(reverse('posts:main_page'))
        self.assertIn('page_obj', initial_response.context)

        initial_response_posts_count = len(
            initial_response.context['page_obj'].object_list)
        self.assertEqual(initial_response_posts_count, Post.objects.count())

        Post.objects.all().delete()

        self.assertEqual(Post.objects.count(), 0)
        cached_response = self.guest_client.get(reverse('posts:main_page'))
        self.assertEqual(initial_response.content, cached_response.content)
        cache.clear()

        clear_response = self.guest_client.get(reverse('posts:main_page'))
        self.assertIn('page_obj', clear_response.context)
        clear_response_posts_count = len(
            clear_response.context['page_obj'].object_list)
        self.assertEqual(clear_response_posts_count, 0)
        self.assertNotEqual(cached_response.content, clear_response.context)
        cache.clear()

    def test_cache_authorized(self):
        initial_response = self.client.get(
            reverse('posts:main_page'))
        self.assertIn('page_obj', initial_response.context)

        initial_response_posts_count = len(
            initial_response.context['page_obj'].object_list)
        self.assertEqual(initial_response_posts_count, Post.objects.count())

        Post.objects.all().delete()

        self.assertEqual(Post.objects.count(), 0)
        cached_response = self.client.get(
            reverse('posts:main_page'))
        self.assertEqual(initial_response.content, cached_response.content)

        cache.clear()

        clear_response = self.client.get(reverse('posts:main_page'))
        self.assertIn('page_obj', clear_response.context)
        clear_response_posts_count = len(
            clear_response.context['page_obj'].object_list)
        self.assertEqual(clear_response_posts_count, 0)
        self.assertNotEqual(cached_response.content, clear_response.context)
        cache.clear()
