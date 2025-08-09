from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView, DetailView
from django.http import HttpResponse
from django.template.response import TemplateResponse
from . models import Category, Product, Size
from django.db.models import Q    # ძებნის რეალიზაციისთვის


class IndexView(TemplateView):
  template_name = 'main/base.html'


  def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context['categories'] = Category.objects.all()
    context['current_category'] = None

    return context
  

  def get(self, request, *args, **kwargs):
    context = self.get_context_data(**kwargs)

    if request.headers.get('HX-Request'):
      return TemplateResponse(request, 'main/home_content.html', context)
    
    return TemplateResponse(request, self.template_name, context)


class CatalogView(TemplateView):
  template_name = 'main/base.html'

  # პროდუქტების სორტირება / ფილტრაცია
  FILTER_MAPPING = {
    'color': lambda queryset, value: queryset.filter(color__iexact=value),
    'min_price': lambda queryset, value: queryset.filter(price__gte=value),
    'max_price': lambda queryset, value: queryset.filter(price__lte=value),
    'size': lambda queryset, value: queryset.filter(product_size__size__name=value),
  }


  def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    category_slug = kwargs.get('category_slug')                 # URL-დან კატეგოორის slug (/catalogs/shoes)
    categories = Category.objects.all()                         # ყველა კატეგორია
    products = Product.objects.all().order_by('-created_at')    # ყველა პროდუქტი (ახლიდან)
    current_category = None

    # კატეგორიის ფილტრაცია
    if category_slug:
      current_category = get_object_or_404(Category, slug=category_slug)
      products = products.filter(category=current_category)
    
    # ძებნის ფუნქციონალი
    query = self.request.GET.get('q')     # ძებნა ხორციელდება url-ზე მიმართვით (URL: ?q=nike)

    if query:
      products = products.filter(
        Q(name__icontains=query) | Q(description__icontains=query)
      )
    
    # დინამიური ფილტრების გამოყენება
    filter_params = {}

    for param, filter_func in self.FILTER_MAPPING.items():
      value = self.request.GET.get(param)           # URL parameter-ის მიღება

      if value:
        products = filter_func(products, value)     # ფილტრის გამოყენება
        filter_params[param] = value                # შენახვა template-სთვის
      else:
        filter_params[param] = ''
      
    filter_params['q'] = query or ''

    # კონტექსტის დაკომპლექტება
    context.update(
      {
        'categories': categories,                 # ყველა კატეგორია ნავიგაციისთვის
        'products': products,                     # გაფილტრული პროდუქტები
        'current_category': category_slug,        # მიმდინარე კატეგორია
        'filter_params': filter_params,           # ყველა ფილტრი form value-ებისთვის
        'sizes': Size.objects.all(),              # size filter dropdown-ისთვის
        'search_query': query or ''               # ძებნის ტექსტი – search input
      }
    )

    # სპეციალური HTMX პარამეტრები / ლოგიკა
    if self.request.GET.get('show_search') == 'true':       # show_search=true -> serarch input ველი
      context['show_search'] = True
    elif self.request.GET.get('reset_search') == 'true':    # reset_search=true -> serarch ღილაკი (reset-ისთვის)
      context['reset_search'] = True

    return context
  

  def get(self, request, *args, **kwargs):
    context = self.get_context_data(**kwargs)

    if request.headers.get('HX-Request'):
      # HTMX-ის სხვადასხვა სცენარები
      if context.get('show_serach'):      # ?show_search=true   ->  serarch_input.html
        return TemplateResponse(request, 'main/search_input.html', context)
      elif context.get('reset_serach'):   # ?reset_search=true  ->  search_button.html
        return TemplateResponse(request, 'main/search_button.html', {})
    
      # ფილტრის მოდალი ან კატალოგი
      template = 'main/filter_modal.html' if request.GET.get('show_filters') == 'true' else 'main/catalog.html'
      # ?show_filters=true  ->  filter_modal.html,   სხვა შემთხვევაში  ->  catalog.html

      return TemplateResponse(request, template, context)

    return TemplateResponse(request, self.template_name, context)


class ProductDetail(DetailView):
  model = Product
  template_name = 'main/base.html'
  slug_field = 'slug'                 # რომელი ველით ვეძებთ მონაცემთა ბაზაში
  slug_url_kwarg = 'slug'             # URL-ის პარამეტრების სახელი


  def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)      # DetailView-ის context + product
    product = self.get_object()                       # მიმდინარე პროდუქტი
    context['categories'] = Category.objects.all()

    # მსგავსი პროდუქტები (იგივე კატეგორია, გარდა მიმდინარე პროდუქტისა, მხოლოდ 4 პროდუქტი)
    context['related_products'] = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]
    context['current_category'] = product.category.slug
    
    return context
  

  def get(self, request, *args, **kwargs):
    context = self.get_context_data(**kwargs)
    self.object = self.get_object()       # პროდუქტის ობიექტი

    if request.headers.get('HX-Request'):
      return TemplateResponse(request, 'main/product_detail.html', context)

    raise TemplateResponse(request, self.template_name, context)