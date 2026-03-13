"""
Custom template tags and filters for the reports app
"""
from django import template
from django.utils.safestring import mark_safe
import re

register = template.Library()


@register.filter(name='format_faqs')
def format_faqs(faq_content):
    """
    Convert FAQ paragraphs into styled FAQ cards.
    
    Input format: Alternating <p> tags for questions and answers
    Output format: Styled FAQ cards with .faq-item, .faq-question, .faq-answer classes
    
    Args:
        faq_content (str): HTML content with FAQ paragraphs
        
    Returns:
        str: Formatted HTML with FAQ cards
    """
    if not faq_content:
        return ''
    
    # Extract all tags (p, h1-h6, li)
    paragraphs = re.findall(r'<(p|h[1-6]|li)>(.*?)</\1>', faq_content, re.DOTALL)
    
    if not paragraphs:
        # Fallback: if no tags found, try to split by double newlines or just return content
        return mark_safe(faq_content)
    
    # Build FAQ cards
    faq_cards = []
    i = 0
    while i < len(paragraphs):
        tag, para = paragraphs[i]
        para = para.strip()
        
        # Skip empty paragraphs
        if not para:
            i += 1
            continue
        
        # Check if this looks like a question
        # 1. It's a heading tag (h1-h6)
        # 2. It's short and doesn't end with a period
        # 3. It ends with a question mark
        # 4. It starts with "Q:" or "Question:"
        is_question = (
            tag.startswith('h') or
            (len(para) < 250 and (not para.endswith('.') or para.endswith('?'))) or
            any(keyword in para.lower() for keyword in ['what', 'why', 'how', 'which', 'who', 'when', 'where', 'faq', 'question']) or
            re.match(r'^(Q|Question|Q\d+)\s*:', para, re.IGNORECASE)
        )
        
        if is_question and i + 1 < len(paragraphs):
            # This is a question, use next paragraph as answer
            question = para
            _, answer = paragraphs[i + 1]
            answer = answer.strip()
            
            # Clean up "Q:" or "A:" prefixes if present
            question = re.sub(r'^(Q|Question|Q\d+)\s*:\s*', '', question, flags=re.IGNORECASE)
            answer = re.sub(r'^(A|Answer|Ans)\s*:\s*', '', answer, flags=re.IGNORECASE)
            
            faq_card = f'''<div class="faq-item">
    <div class="faq-question">{question}</div>
    <div class="faq-answer">{answer}</div>
</div>'''
            faq_cards.append(faq_card)
            i += 2  # Skip both question and answer
        else:
            # Not a clear Q&A pair, render as answer/text in a card
            faq_card = f'''<div class="faq-item">
    <div class="faq-answer">{para}</div>
</div>'''
            faq_cards.append(faq_card)
            i += 1
    
    return mark_safe('\n'.join(faq_cards))


@register.filter(name='extract_companies')
def extract_companies(content):
    """
    Extract company names from HTML content (usually bullet points).
    Used for the 'Key Players' sidebar widget.
    """
    if not content:
        return []
        
    # Find all list items or strong tags which usually contain company names
    companies = re.findall(r'<li>(.*?)</li>|<strong>(.*?)</strong>', content)
    
    unique_companies = []
    for comp in companies:
        # comp is a tuple because of two capturing groups
        name = comp[0] or comp[1]
        # Clean up tags and extra whitespace
        name = re.sub(r'<[^>]+>', '', name).strip()
        # Filter out common phrases or short abbreviations
        if name and len(name) > 2 and len(name) < 100:
            if name not in unique_companies:
                unique_companies.append(name)
                
                
    return unique_companies[:30]  # Limit to 30 companies


@register.filter(name='downgrade_headers')
def downgrade_headers(value):
    """
    Downgrade all header tags (h1-h6) to simple paragraphs to match surrounding text.
    """
    if not value:
        return value
    # Replace h1-h6 opening tags with p
    value = re.sub(r'<h[1-6]>', '<p>', value)
    # Replace closing tags
    value = re.sub(r'</h[1-6]>', '</p>', value)
    return mark_safe(value)


@register.filter(name='get_category_icon')
def get_category_icon(category_name):
    """
    Return an emoji icon based on the category name.
    """
    if not category_name:
        return '📊'
    
    name = category_name.lower()
    
    if "health" in name or "pharma" in name or "bio" in name:
        return '🩺'
    elif "tech" in name or "software" in name or "cyber" in name:
        return '💻'
    elif "chem" in name or "material" in name:
        return '⚗️'
    elif "energy" in name or "power" in name:
        return '⚡'
    elif "auto" in name or "vehicle" in name:
        return '🚗'
    elif "food" in name or "beverage" in name:
        return '🍔'
    elif "aero" in name or "defence" in name or "security" in name:
        return '✈️'
    elif "consumer" in name or "retail" in name:
        return '🛍️'
    else:
        return '📊'


@register.filter(name='format_market_coverage')
def format_market_coverage(content):
    """
    Convert market coverage content (lists or paragraphs) into a styled, attractive table.
    Handles separators like ':' and '|'.
    """
    if not content:
        return ''
    
    # If it's already a table, mark as safe but try to strip some basic tags if they look like the messy ones
    if '<table' in content.lower() and 'border-collapse' not in content:
        # It's a raw table from somewhere else, we might want to let it through 
        # but the goal is to standardize. For now, let's process if it doesn't look like our styled table.
        pass
    
    # Extract items
    items = re.findall(r'<li>(.*?)</li>', content, re.DOTALL)
    if not items:
        items = re.findall(r'<p>(.*?)</p>', content, re.DOTALL)
    if not items:
        clean_content = re.sub(r'<[^>]+>', '\n', content)
        items = [line.strip() for line in clean_content.split('\n') if line.strip()]

    rows = []
    is_first = True
    
    for item in items:
        clean_item = re.sub(r'<(?!strong|b|em|i)[^>]+>', '', item).strip()
        if not clean_item: continue

        sep = '|' if '|' in clean_item else ':' if ':' in clean_item else None
        
        if sep:
            parts = clean_item.split(sep, 1)
            key = parts[0].strip()
            key_clean = re.sub(r'<[^>]+>', '', key)
            value = parts[1].strip()
            
            if is_first and (key_clean.lower() == 'parameter' or key_clean.lower() == 'details'):
                # Header row styling - Simple Gray
                rows.append(f'''
                <tr style="background: #1e3a8a; border-bottom: 2px solid #1e3a8a;">
                    <th style="padding: 1rem 1.25rem; font-weight: 700; color: #ffffff; width: 40%; text-transform: uppercase; font-size: 0.8rem; letter-spacing: 0.05em; font-family: 'Outfit', sans-serif;">{key_clean}</th>
                    <th style="padding: 1rem 1.25rem; font-weight: 700; color: #ffffff; text-transform: uppercase; font-size: 0.8rem; letter-spacing: 0.05em; font-family: 'Outfit', sans-serif;">{value}</th>
                </tr>''')
                is_first = False
                continue

            rows.append(f'''
            <tr style="border-bottom: 1px solid #e2e8f0;">
                <td style="padding: 1rem 1.25rem; font-weight: 600; color: #1e3a8a; background: #ffffff; width: 40%; font-size: 0.95rem; font-family: 'Outfit', sans-serif;">
                    {key_clean}
                </td>
                <td style="padding: 1rem 1.25rem; color: #334155; font-size: 0.95rem; line-height: 1.5; background: #ffffff; font-family: 'Outfit', sans-serif;">
                    {value}
                </td>
            </tr>''')
            is_first = False
        else:
            rows.append(f'''
            <tr style="border-bottom: 1px solid #f1f5f9;">
                <td colspan="2" style="padding: 1.1rem 1.5rem; color: #64748b; font-style: italic; background: #f8fafc; font-size: 0.95rem; font-family: 'Outfit', sans-serif;">
                    {clean_item}
                </td>
            </tr>''')

    if not rows:
        return mark_safe(content)
        
    table_html = f'''
    <div class="market-coverage-wrapper" style="margin: 1rem 0 2rem 0; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; background: white;">
        <table style="width: 100%; border-collapse: collapse; text-align: left;">
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
    </div>
    '''
    return mark_safe(table_html)


@register.filter(name='format_list')
def format_list(content):
    """
    Convert content into a clean bulleted list with tight spacing.
    Extracts text from paragraphs or headers if necessary.
    """
    if not content:
        return ''
    
    # If it already has list tags, just wrap and adjust gaps via CSS if needed
    if '<li>' in content.lower():
        # Add tight-list class for styling
        return mark_safe(f'<div class="tight-list-container">{content}</div>')

    # Extract text from p, h1, h2 etc.
    lines = re.findall(r'<(?:p|h[1-6])>(.*?)</(?:p|h[1-6])>', content, re.DOTALL)
    if not lines:
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
    if not lines:
        return mark_safe(content)
        
    li_items = []
    for line in lines:
        # Strip any existing internal tags to avoid nested mess
        clean_text = re.sub(r'<[^>]+>', '', line).strip()
        if clean_text:
            li_items.append(f'<li style="margin-bottom: 0.4rem; color: #334155; font-weight: 500; font-size: 1.2rem;">{clean_text}</li>')
            
    if not li_items:
        return mark_safe(content)
        
    return mark_safe(f'<ul style="list-style-type: disc; padding-left: 1.5rem; margin: 1rem 0;">{"".join(li_items)}</ul>')


@register.filter(name='format_segmentation')
def format_segmentation(content):
    """
    Format market segmentation content:
    - Bold and Blue color for 'By XYZ' segments
    - Bullet points for sub-segments
    """
    if not content:
        return ''
    
    # Normalize by converting tags to newlines to extract clean lines
    text = re.sub(r'<(?:br|p|h[1-6]|li)[^>]*>', '\n', content)
    text = re.sub(r'</(?:p|h[1-6]|li)>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    formatted_output = []
    current_list = []
    
    for line in lines:
        # Check if line starts with "By " (case insensitive)
        if re.match(r'^By\s+', line, re.IGNORECASE):
            # Close previous list
            if current_list:
                formatted_output.append(f'<ul style="list-style-type: disc; padding-left: 2rem; margin-bottom: 1.5rem;">{"".join(current_list)}</ul>')
                current_list = []
            
            # Style header (Blue & Bold)
            formatted_output.append(f'<div style="font-weight: 800; color: #1e3a8a; font-size: 1.3rem; margin-top: 1.8rem; margin-bottom: 0.8rem;">{line}</div>')
        else:
            # Add to bullet list
            current_list.append(f'<li style="margin-bottom: 0.5rem; color: #334155; font-size: 1.15rem; font-weight: 500;">{line}</li>')

    # Close final list
    if current_list:
        formatted_output.append(f'<ul style="list-style-type: disc; padding-left: 2rem; margin-bottom: 1.5rem;">{"".join(current_list)}</ul>')
        
    if not formatted_output:
        return mark_safe(content)
        
    return mark_safe("".join(formatted_output))


@register.filter(name='get_category_image_url')
def get_category_image_url(category_name):
    """
    Return the path to the category image based on the category name.
    Handles mapping between full category names and available image files.
    """
    if not category_name:
        return '/static/images/default_category.jpg'
    
    mapping = {
        'Aerospace, Defense & Security': 'Aerospace, Defense & Security.jpg',
        'Chemicals, Materials & Polymers': 'Chemicals.jpg',
        'FMCG & Consumer Products': 'FMCG.jpg',
        'Healthcare & Life Sciences': 'Healthcare.jpg',
        'Heavy Machinery & Equipment': 'Heavy Machinery.jpg',
        'Industrial Automation & Mobility': 'Industrial Automation.jpg',
        'Information Technology & Electronics': 'Information Technology.jpg',
        # Add simpler keys just in case
        'Aerospace': 'Aerospace, Defense & Security.jpg',
        'Defense': 'Aerospace, Defense & Security.jpg',
        'Chemicals': 'Chemicals.jpg',
        'FMCG': 'FMCG.jpg',
        'Healthcare': 'Healthcare.jpg',
        'Machinery': 'Heavy Machinery.jpg',
        'Automation': 'Industrial Automation.jpg',
        'IT': 'Information Technology.jpg',
        'Information Technology': 'Information Technology.jpg'
    }
    
    # Try exact match first
    filename = mapping.get(category_name)
    if filename:
        return f'/static/images/{filename}'
        
    # Try partial matching if strict match fails
    for key, val in mapping.items():
        if key in category_name:
            return f'/static/images/{val}'
            
    # Fallback: try to use the name directly (assuming it matches a file)
    return f'/static/images/{category_name}.jpg'
