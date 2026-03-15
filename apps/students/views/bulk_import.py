from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string
import json
import logging

from ..forms import BulkStudentImportForm
from ..services.bulk_operations import BulkStudentService

logger = logging.getLogger(__name__)


@login_required
@permission_required('students.bulk_import_students')
def bulk_import(request):
    """Bulk import students view"""
    
    if request.method == 'POST':
        form = BulkStudentImportForm(request.POST, request.FILES, user=request.user)
        
        # Check if this is a preview request
        if request.POST.get('preview'):
            if form.is_valid():
                try:
                    preview_data, stats = form.get_preview_data()
                    return JsonResponse({
                        'preview_data': preview_data,
                        'stats': stats
                    })
                except Exception as e:
                    logger.error(f"Preview failed: {e}", exc_info=True)
                    return JsonResponse({'error': str(e)}, status=400)
            else:
                return JsonResponse({'errors': form.errors.get_json_data()}, status=400)
        
        # Process actual import
        if form.is_valid():
            try:
                preview_data, stats = form.get_preview_data()
                
                # Filter valid records
                valid_records = [r for r in preview_data if r['valid']]
                
                # Process import
                results = BulkStudentService.process_import(
                    records=valid_records,
                    options=form.cleaned_data,
                    user=request.user
                )
                
                messages.success(
                    request,
                    f"Successfully imported {results['success']} students. "
                    f"{results['failed']} failed, {results['skipped']} skipped."
                )
                
                return redirect('students:list')
                
            except Exception as e:
                logger.error(f"Import failed: {e}", exc_info=True)
                messages.error(request, f"Import failed: {str(e)}")
                return render(request, 'students/bulk_import.html', {'form': form})
    else:
        form = BulkStudentImportForm(user=request.user)
    
    return render(request, 'students/bulk_import.html', {
        'form': form,
        'template_context': form.get_template_context()
    })


@login_required
@permission_required('students.bulk_import_students')
@require_http_methods(["POST"])
def render_preview(request):
    """Render preview HTML from JSON data"""
    try:
        data = json.loads(request.body)
        preview_data = data.get('preview_data', [])
        stats = data.get('stats', {})
        
        html = render_to_string('students/partials/preview_results.html', {
            'preview_data': json.dumps(preview_data),
            'stats': stats,
            'csrf_token': request.COOKIES.get('csrftoken', '')
        })
        
        return JsonResponse({'html': html})
        
    except Exception as e:
        logger.error(f"Render preview failed: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@permission_required('students.bulk_import_students')
@require_http_methods(["POST"])
def confirm_import(request):
    """Confirm and process import"""
    try:
        data = json.loads(request.body)
        preview_data = data.get('preview_data', [])
        stats = data.get('stats', {})
        
        # Filter valid records
        valid_records = [r for r in preview_data if r.get('valid')]
        
        # Process import
        results = BulkStudentService.process_import(
            records=valid_records,
            options={
                'create_user_accounts': request.POST.get('create_user_accounts') == 'on',
                'send_welcome_emails': request.POST.get('send_welcome_emails') == 'on',
                'update_existing': request.POST.get('update_existing') == 'on',
            },
            user=request.user
        )
        
        return JsonResponse({
            'success': True,
            'results': results,
            'redirect_url': reverse('students:list')
        })
        
    except Exception as e:
        logger.error(f"Confirm import failed: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=400)
        
