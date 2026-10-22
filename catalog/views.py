from django.shortcuts import render
from django.views import generic
from .models import Book, Author, BookInstance, Genre


def index(request):
    """View function for home page of site."""

    num_books = Book.objects.all().count()
    num_instances = BookInstance.objects.all().count()

    # Available books (status = 'a')
    num_instances_available = BookInstance.objects.filter(status__exact='a').count()

    num_authors = Author.objects.count()

    # Challenge: count genres, and books containing a specific word
    num_genres = Genre.objects.filter(name__icontains='fiction').count()
    num_books_containing_word = Book.objects.filter(title__icontains='the').count()

    context = {
        'num_books': num_books,
        'num_instances': num_instances,
        'num_instances_available': num_instances_available,
        'num_authors': num_authors,
        'num_genres': num_genres,
        'num_books_containing_word': num_books_containing_word,
    }

    return render(request, 'index.html', context=context)


class BookListView(generic.ListView):
    model = Book
    paginate_by = 10
    # Avoids one extra query per book when templates loop over book.bookauthor_set
    queryset = Book.objects.prefetch_related('bookauthor_set__author')


class BookDetailView(generic.DetailView):
    model = Book
    queryset = Book.objects.prefetch_related('bookauthor_set__author')


class AuthorListView(generic.ListView):
    model = Author
    paginate_by = 10


class AuthorDetailView(generic.DetailView):
    model = Author
    queryset = Author.objects.prefetch_related('books')