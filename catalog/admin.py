from django.contrib import admin # type: ignore
from .models import Author, Genre, Book, BookInstance, Language, BookAuthor


class BooksInstanceInline(admin.TabularInline):
    model = BookInstance
    extra = 0


class BookAuthorInline(admin.TabularInline):
    model = BookAuthor
    extra = 0


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'date_of_birth', 'date_of_death')
    inlines = [BookAuthorInline]


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'display_authors', 'display_genre')
    inlines = [BookAuthorInline, BooksInstanceInline]

    def display_authors(self, obj):
        """Authors in order, comma separated."""
        return ', '.join(str(ba.author) for ba in obj.bookauthor_set.all())

    display_authors.short_description = 'Authors'


@admin.register(BookInstance)
class BookInstanceAdmin(admin.ModelAdmin):
    list_display = ('book', 'status', 'borrower', 'due_back', 'id')
    list_filter = ('status', 'due_back')
    fieldsets = (
        (None, {
            'fields': ('book', 'imprint', 'id')
        }),
        ('Availability', {
            'fields': ('status', 'due_back', 'borrower')
        }),
    )


admin.site.register(Genre)
admin.site.register(Language)