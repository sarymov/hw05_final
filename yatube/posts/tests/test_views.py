import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Follow, Group, Post, User

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.image = uploaded
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.user,
            group=cls.group,
            image=cls.image,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_pages_uses_correct_template(self):
        templates_pages_names = {
            reverse('posts:main_page'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': self.group.slug}):
            'posts/group_list.html',
            reverse('posts:profile', kwargs={
                'username': self.post.author.username}):
            'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}):
            'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}):
            'posts/create_post.html',
        }

        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        response = self.authorized_client.get(reverse('posts:main_page'))
        self.assertEqual(response.context.get('page_obj')[0], self.post)
        # По неведомым для меня причинам - если убрать ниже cache.clear(),
        # ломается этот тест со словами NoneType object has no
        # attribure 'get'. '''
        cache.clear()

        response = self.guest_client.get(reverse('posts:main_page'))
        self.assertEqual(response.context.get('page_obj')[0], self.post)

    def test_group_list_correct_context(self):
        response = reverse(
            'posts:group_list', kwargs={'slug': self.group.slug})
        response = self.authorized_client.get(response)
        self.assertEqual(response.context.get('group'), self.group)

        response = reverse(
            'posts:group_list', kwargs={'slug': self.group.slug})
        response = self.guest_client.get(response)
        self.assertEqual(response.context.get('group'), self.group)

    def test_profile_correct_context(self):
        response = reverse('posts:profile', kwargs={'username': self.user})
        response = self.authorized_client.get(response)
        self.assertEqual(response.context.get('author'), self.user)

        response = reverse('posts:profile', kwargs={'username': self.user})
        response = self.guest_client.get(response)
        self.assertEqual(response.context.get('author'), self.user)

    def test_post_detail_correct_context(self):
        response = reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id})
        response = self.authorized_client.get(response)
        self.assertEqual(response.context.get('post').id, self.post.id)

        response = reverse('posts:profile', kwargs={'username': self.user})
        response = self.guest_client.get(response)
        self.assertEqual(response.context.get('author'), self.user)

    def test_post_create_correct_context(self):
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_post_edit_correct_context(self):
        url = reverse('posts:post_edit', kwargs={'post_id': self.post.id})
        response = self.authorized_client.get(url)
        self.assertEqual(response.context.get('post').id, self.post.id)

    def test_create_post_in_page_group(self):
        form_fields = {
            reverse("posts:main_page"):
            Post.objects.get(group=self.post.group),
            reverse(
                "posts:group_list", kwargs={"slug": 'test-slug'}
            ): Post.objects.get(group=self.post.group),
            reverse(
                "posts:profile", kwargs={"username": 'auth'}
            ): Post.objects.get(group=self.post.group),
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                form_field = response.context['page_obj']
                self.assertIn(expected, form_field)

    def test_post_do_not_go_to_another_group(self):
        form_fields = {
            reverse(
                "posts:group_list", kwargs={"slug": 'test-slug'}
            ): Post.objects.exclude(group=self.post.group),
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                form_field = response.context["page_obj"]
                self.assertNotIn(expected, form_field)


class PaginatorModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.test_posts: list = []
        for i in range(15):
            cls.test_posts.append(
                Post.objects.create(
                    author=cls.user,
                    text=f'Тестовый пост {i}',
                    group=cls.group,
                )
            )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PaginatorModelTest.user)

    def test_index_paginator(self):
        response = self.authorized_client.get(reverse('posts:main_page'))
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_index_next_page(self):
        response = self.authorized_client.get(
            reverse('posts:main_page') + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 5)

    def test_group_list_paginator(self):
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': 'test-slug'})
        )
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_group_list_paginator(self):
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={
                'slug': 'test-slug'}) + '?page=2'
        )
        self.assertEqual(len(response.context['page_obj']), 5)

    def test_profile_paginator(self):
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': f'{self.user}'})
        )
        self.assertEqual(len(response.context['page_obj']), 10)


class FollowTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.subscriber = User.objects.create_user(username='follower')
        cls.author = User.objects.create_user(username='following')
        cls.subscriber_2 = User.objects.create_user(
            username='subscriber_2')
        cls.follow = Follow.objects.create(
            user=cls.subscriber,
            author=cls.author,
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.author,
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.subscriber)
        self.subscriber_2_client = Client()
        self.subscriber_2_client.force_login(self.subscriber_2)
        cache.clear()

    def test_follow_index(self):
        response = self.authorized_client.get(reverse(
            'posts:follow_index'
        ))
        follower_posts = len(response.context['page_obj'])
        self.assertEqual(follower_posts, 1)
        post = Post.objects.get(id=self.post.pk)
        self.assertIn(post, response.context['page_obj'])

    def test_follow(self):
        self.authorized_client.get(
            reverse('posts:profile_follow', kwargs={'username': self.author})
        )
        self.assertTrue(Follow.objects.filter(
            user=self.subscriber,
            author=self.author,
        ).exists())

    def test_unfollow(self):
        response = self.subscriber_2_client.get(reverse(
            'posts:follow_index'))
        posts_new = len(response.context['page_obj'].object_list)
        self.assertEqual(posts_new, 0)
