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
    
    # Extract all <p> tags
    paragraphs = re.findall(r'<p>(.*?)</p>', faq_content, re.DOTALL)
    
    if not paragraphs:
        return faq_content
    
    # Build FAQ cards
    faq_cards = []
    i = 0
    while i < len(paragraphs):
        para = paragraphs[i].strip()
        
        # Skip empty paragraphs
        if not para:
            i += 1
            continue
        
        # Check if this looks like a question (short, no period at end, or ends with ?)
        # Questions are typically shorter and don't have long explanatory text
        is_question = (
            len(para) < 200 and 
            (not para.endswith('.') or para.endswith('?') or 
             any(keyword in para.lower() for keyword in ['what', 'why', 'how', 'which', 'who', 'when', 'where']))
        )
        
        if is_question and i + 1 < len(paragraphs):
            # This is a question, next paragraph is the answer
            question = para
            answer = paragraphs[i + 1].strip()
            
            faq_card = f'''<div class="faq-item">
    <div class="faq-question">{question}</div>
    <div class="faq-answer">{answer}</div>
</div>'''
            faq_cards.append(faq_card)
            i += 2  # Skip both question and answer
        else:
            # Not a Q&A pair, just render as-is in a card
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
