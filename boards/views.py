from django.db.models import Count
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import UpdateView, ListView
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.urls import reverse
from django.db.models import Q, Count

from myproject.utils import recaptcha_is_valid

from .forms import NewBoardForm, NewTopicForm, PostForm
from .models import Board, Post, Topic


class BoardListView(ListView):
    model = Board
    context_object_name = 'boards'
    template_name = 'home.html'

    def get_queryset(self):
        queryset = Board.objects.filter(Q(private=False))
        if self.request.user.is_authenticated():
            queryset = Board.objects.filter(Q(private=False) | Q(private=True, members__in=[self.request.user]) 
                | Q(owner=self.request.user)).distinct()
        return queryset


@method_decorator(login_required, name='dispatch')
class BoardUpdateView(UpdateView):
    model = Board
    form_class = NewBoardForm
    template_name = 'edit_board.html'
    context_object_name = 'board'

    def form_valid(self, form):
        board = form.save(commit=False)
        board.save()
        form.save_m2m()
        return redirect('board_topics', board.pk)


class TopicListView(ListView):
    model = Topic
    context_object_name = 'topics'
    template_name = 'topics.html'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        kwargs['board'] = self.board
        return super().get_context_data(**kwargs)

    def get_queryset(self):
        if self.request.user.is_authenticated():
            queryset = Board.objects.filter((Q(private=False) | Q(private=True, members__in=[self.request.user]) 
                | Q(owner=self.request.user)) & (Q(pk=self.kwargs.get('pk')))
            ).distinct()
            self.board = get_object_or_404(queryset)
        else:
            self.board = get_object_or_404(Board, Q(private=False, pk=self.kwargs.get('pk')) )
        queryset = self.board.topics.order_by('-last_updated').annotate(replies=Count('posts') - 1)
        return queryset


class PostListView(ListView):
    model = Post
    context_object_name = 'posts'
    template_name = 'topic_posts.html'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        session_key = 'viewed_topic_{}'.format(self.topic.pk)
        if not self.request.session.get(session_key, False):
            self.topic.views += 1
            self.topic.save()
            self.request.session[session_key] = True
        kwargs['topic'] = self.topic
        return super().get_context_data(**kwargs)

    def get_queryset(self):
        self.topic = get_object_or_404(Topic, board__pk=self.kwargs.get('pk'), pk=self.kwargs.get('topic_pk'))
        queryset = self.topic.posts.order_by('created_at')
        return queryset


@login_required
def new_board(request):
    if request.method == 'POST':
        form = NewBoardForm(request.POST)
        if form.is_valid() and recaptcha_is_valid(request):
            board = form.save(commit=False)
            board.owner = request.user
            board.save()
            form.save_m2m()
            return redirect('home')
    else:
        form = NewBoardForm()
    return render(request, 'new_board.html', {'form': form})


@login_required
def new_topic(request, pk):
    board = get_object_or_404(Board, pk=pk)
    if request.method == 'POST':
        form = NewTopicForm(request.POST)
        if form.is_valid() and recaptcha_is_valid(request):
            topic = form.save(commit=False)
            topic.board = board
            topic.starter = request.user
            topic.save()
            Post.objects.create(
                message=form.cleaned_data.get('message'),
                topic=topic,
                created_by=request.user
            )
            return redirect('topic_posts', pk=pk, topic_pk=topic.pk)
    else:
        form = NewTopicForm()
    return render(request, 'new_topic.html', {'board': board, 'form': form})


@login_required
def reply_topic(request, pk, topic_pk):
    topic = get_object_or_404(Topic, board__pk=pk, pk=topic_pk)
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid() and recaptcha_is_valid(request):
            post = form.save(commit=False)
            post.topic = topic
            post.created_by = request.user
            post.save()

            topic.last_updated = timezone.now()
            topic.save()

            topic_url = reverse('topic_posts', kwargs={'pk': pk, 'topic_pk': topic_pk})
            topic_post_url = '{url}?page={page}#{id}'.format(
                url=topic_url,
                id=post.pk,
                page=topic.get_page_count()
            )

            return redirect(topic_post_url)
    else:
        form = PostForm()
    return render(request, 'reply_topic.html', {'topic': topic, 'form': form})


@method_decorator(login_required, name='dispatch')
class PostUpdateView(UpdateView):
    model = Post
    fields = ('message', )
    template_name = 'edit_post.html'
    pk_url_kwarg = 'post_pk'
    context_object_name = 'post'

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(created_by=self.request.user)

    def form_valid(self, form):
        post = form.save(commit=False)
        post.updated_by = self.request.user
        post.updated_at = timezone.now()
        post.save()
        return redirect('topic_posts', pk=post.topic.board.pk, topic_pk=post.topic.pk)
