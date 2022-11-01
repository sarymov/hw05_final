from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django import forms
from django.core.cache import cache
from posts.models import Group, Post, User

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
        )

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
        first_object = response.context['page_obj'][0]
        post_author_0 = first_object.author
        post_text_0 = first_object.text
        post_group_0 = first_object.group
        self.assertEqual(post_author_0, PostURLTests.user)
        self.assertEqual(post_text_0, 'Тестовый пост')
        self.assertEqual(post_group_0, PostURLTests.post.group)
        self.assertIn('page_obj', response.context)

    def test_group_list_correct_context(self):
        response = (self.authorized_client.
                    get(reverse(
                        'posts:group_list', kwargs={'slug': 'test-slug'}))
                    )
        self.assertEqual(
            response.context.get('group').title, 'Тестовая группа'
        )
        self.assertEqual(
            response.context.get('group').description, 'Тестовое описание'
        )
        self.assertEqual(response.context.get('group').slug, 'test-slug')

    def test_profile_correct_context(self):
        response = (self.authorized_client.
                    get(reverse('posts:profile', kwargs={'username': 'auth'}))
                    )
        self.assertEqual(response.context['author'].username, 'auth')

    def test_post_detail_correct_context(self):
        response = (self.authorized_client.
                    get(reverse(
                        'posts:post_detail',
                        kwargs={'post_id': f'{self.post.id}'}))
                    )
        self.assertEqual(
            response.context['post'].id, int(f'{self.post.id}')
        )

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
        response = (self.authorized_client.
                    get(reverse(
                        'posts:post_edit',
                        kwargs={"post_id": f'{self.post.id}'}))
                    )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)
        self.assertTrue(response.context['form'])

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
                form_field = response.context["page_obj"]
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
        for i in range(10):
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

    def test_group_list_paginator(self):
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': 'test-slug'})
        )
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_profile_paginator(self):
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': f'{self.user}'})
        )
        self.assertEqual(len(response.context['page_obj']), 10)
