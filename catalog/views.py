import datetime

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.forms import inlineformset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.views import generic
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from .forms import RenewBookForm
from .models import Author, Book, BookAuthor, BookInstance, Genre


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

    # Number of visits to this view, as counted in the session variable.
    num_visits = request.session.get('num_visits', 0)
    num_visits += 1
    request.session['num_visits'] = num_visits

    context = {
        'num_books': num_books,
        'num_instances': num_instances,
        'num_instances_available': num_instances_available,
        'num_authors': num_authors,
        'num_genres': num_genres,
        'num_books_containing_word': num_books_containing_word,
        'num_visits': num_visits,
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


class LoanedBooksByUserListView(LoginRequiredMixin, generic.ListView):
    """Generic class-based view listing books on loan to current user."""
    model = BookInstance
    template_name = 'catalog/bookinstance_list_borrowed_user.html'
    paginate_by = 10

    def get_queryset(self):
        return (
            BookInstance.objects.filter(borrower=self.request.user)
            .filter(status__exact='o')
            .order_by('due_back')
        )


class AllLoanedBooksListView(PermissionRequiredMixin, generic.ListView):
    """Librarians only: all books currently on loan, with borrowers."""
    model = BookInstance
    permission_required = 'catalog.can_mark_returned'
    template_name = 'catalog/bookinstance_list_borrowed_all.html'
    paginate_by = 10

    def get_queryset(self):
        return (
            BookInstance.objects.filter(status__exact='o')
            .select_related('book', 'borrower')
            .order_by('due_back')
        )


@login_required
@permission_required('catalog.can_mark_returned', raise_exception=True)
def renew_book_librarian(request, pk):
    """View function for renewing a specific BookInstance by librarian."""
    book_instance = get_object_or_404(BookInstance, pk=pk)

    # If this is a POST request then process the Form data
    if request.method == 'POST':

        # Create a form instance and populate it with data from the request (binding):
        form = RenewBookForm(request.POST)

        # Check if the form is valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required (here we just write it to the model due_back field)
            book_instance.due_back = form.cleaned_data['renewal_date']
            book_instance.save()

            # redirect to a new URL:
            return HttpResponseRedirect(reverse('all-borrowed'))

    # If this is a GET (or any other method) create the default form.
    else:
        proposed_renewal_date = datetime.date.today() + datetime.timedelta(weeks=3)
        form = RenewBookForm(initial={'renewal_date': proposed_renewal_date})

    context = {
        'form': form,
        'book_instance': book_instance,
    }

    return render(request, 'catalog/book_renew_librarian.html', context)


AUTHOR_FIELDS = ['first_name', 'last_name', 'date_of_birth', 'date_of_death']


class AuthorCreate(PermissionRequiredMixin, CreateView):
    model = Author
    fields = AUTHOR_FIELDS
    permission_required = 'catalog.add_author'


class AuthorUpdate(PermissionRequiredMixin, UpdateView):
    model = Author
    fields = AUTHOR_FIELDS
    permission_required = 'catalog.change_author'


class AuthorDelete(PermissionRequiredMixin, DeleteView):
    model = Author
    success_url = reverse_lazy('authors')
    permission_required = 'catalog.delete_author'

    def form_valid(self, form):
        # BookAuthor rows cascade, so refuse here instead of silently unlinking the author from books.
        if self.object.books.exists():
            return HttpResponseRedirect(reverse('author-delete', kwargs={'pk': self.object.pk}))
        try:
            self.object.delete()
            return HttpResponseRedirect(self.success_url)
        except Exception:
            return HttpResponseRedirect(reverse('author-delete', kwargs={'pk': self.object.pk}))


# Books have many authors through BookAuthor (which needs author_order), so the authors
# are edited with an inline formset instead of a plain multi-select field.
BookAuthorFormSet = inlineformset_factory(
    Book, BookAuthor, fields=['author', 'author_order'], extra=2)

BOOK_FIELDS = ['title', 'summary', 'isbn', 'genre', 'language']


class BookAuthorFormSetMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.method == 'POST':
            context['author_formset'] = BookAuthorFormSet(self.request.POST, instance=self.object)
        else:
            context['author_formset'] = BookAuthorFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        author_formset = BookAuthorFormSet(self.request.POST, instance=form.instance)
        if not author_formset.is_valid():
            return self.form_invalid(form)
        self.object = form.save()
        author_formset.instance = self.object
        author_formset.save()
        return HttpResponseRedirect(self.get_success_url())


class BookCreate(PermissionRequiredMixin, BookAuthorFormSetMixin, CreateView):
    model = Book
    fields = BOOK_FIELDS
    permission_required = 'catalog.add_book'


class BookUpdate(PermissionRequiredMixin, BookAuthorFormSetMixin, UpdateView):
    model = Book
    fields = BOOK_FIELDS
    permission_required = 'catalog.change_book'


class BookDelete(PermissionRequiredMixin, DeleteView):
    model = Book
    success_url = reverse_lazy('books')
    permission_required = 'catalog.delete_book'

    def form_valid(self, form):
        try:
            self.object.delete()
            return HttpResponseRedirect(self.success_url)
        except Exception:
            # BookInstance uses RESTRICT, so a book with copies can't be deleted.
            return HttpResponseRedirect(reverse('book-delete', kwargs={'pk': self.object.pk}))
