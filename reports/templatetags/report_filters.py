"""
Custom template tags and filters for the reports app
"""
from django import template
from django.urls import reverse
from django.utils.safestring import mark_safe
import re

register = template.Library()


@register.filter(name='format_faqs')
def format_faqs(faq_content):
    """
    Convert FAQ paragraphs into styled FAQ cards.
    """
    if not faq_content:
        return ''
    
    # Extract all tags (p, h1-h6, li)
    paragraphs = re.findall(r'<(p|h[1-6]|li)>(.*?)</\1>', faq_content, re.DOTALL)
    
    if not paragraphs:
        return mark_safe(faq_content)
    
    faq_cards = []
    card_count = 1
    i = 0
    while i < len(paragraphs):
        tag, para = paragraphs[i]
        para = para.strip()
        
        if not para:
            i += 1
            continue
        
        # Determine if this is a question
        is_question = (
            tag.startswith('h') or
            (len(para) < 250 and (not para.endswith('.') or para.endswith('?'))) or
            any(keyword in para.lower() for keyword in ['what', 'why', 'how', 'which', 'who', 'when', 'where', 'faq', 'question']) or
            re.match(r'^(Q|Question|Q\d+)\s*:', para, re.IGNORECASE)
        )
        
        if is_question and i + 1 < len(paragraphs):
            question = para
            _, answer = paragraphs[i + 1]
            answer = answer.strip()
            
            # Clean prefixes
            question = re.sub(r'^(Q|Question|Q\d+)\s*[:.]\s*', '', question, flags=re.IGNORECASE)
            question = re.sub(r'<[^>]+>', '', question)
            answer = re.sub(r'^(A|Answer|Ans)\s*[:.]\s*', '', answer, flags=re.IGNORECASE)
            
            faq_card = f'''
<div class="faq-accordion-item">
    <button class="faq-accordion-header" type="button">
        <span class="faq-question-text"><span class="q-num">Q{card_count}.</span> {question}</span>
        <span class="faq-arrow">▼</span>
    </button>
    <div class="faq-accordion-content">
        <div class="faq-answer-inner">{answer}</div>
    </div>
</div>'''
            faq_cards.append(faq_card)
            card_count += 1
            i += 2
        else:
            # Fallback for single blocks
            faq_card = f'''
<div class="faq-accordion-item">
    <div class="faq-answer-inner">{para}</div>
</div>'''
            faq_cards.append(faq_card)
            i += 1
    
    return mark_safe('\n'.join(faq_cards))


@register.filter(name='extract_companies')
def extract_companies(content):
    """Extract company names from HTML content."""
    if not content:
        return []
        
    companies = re.findall(r'<li>(.*?)</li>|<strong>(.*?)</strong>', content)
    unique_companies = []
    for comp in companies:
        name = comp[0] or comp[1]
        name = re.sub(r'<[^>]+>', '', name).strip()
        if name and len(name) > 2 and len(name) < 100:
            if name not in unique_companies:
                unique_companies.append(name)
                
    return unique_companies[:30]


@register.filter(name='downgrade_headers')
def downgrade_headers(value):
    """Downgrade all header tags to paragraphs."""
    if not value:
        return value
    value = re.sub(r'<h[1-6]>', '<p>', value)
    value = re.sub(r'</h[1-6]>', '</p>', value)
    return mark_safe(value)


@register.filter(name='get_category_icon')
def get_category_icon(category_name):
    """Return an emoji icon based on category."""
    if not category_name:
        return '📊'
    name = category_name.lower()
    if any(k in name for k in ["health", "pharma", "bio"]): return '🩺'
    if any(k in name for k in ["tech", "software", "cyber"]): return '💻'
    if any(k in name for k in ["chem", "material"]): return '⚗️'
    if any(k in name for k in ["energy", "power"]): return '⚡'
    if any(k in name for k in ["auto", "vehicle"]): return '🚗'
    if any(k in name for k in ["food", "beverage"]): return '🍔'
    if any(k in name for k in ["aero", "defence", "security"]): return '✈️'
    if any(k in name for k in ["consumer", "retail"]): return '🛍️'
    return '📊'


@register.filter(name='format_market_coverage')
def format_market_coverage(content):
    """Convert content into a styled table."""
    if not content: return ''
    items = re.findall(r'<li>(.*?)</li>', content, re.DOTALL)
    if not items: items = re.findall(r'<p>(.*?)</p>', content, re.DOTALL)
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
                rows.append(f'''<tr style="background: #1e3a8a; border-bottom: 2px solid #1e3a8a;"><th style="padding: 1rem 1.25rem; font-weight: 700; color: #ffffff; width: 40%; text-transform: uppercase; font-size: 1rem; letter-spacing: 0.05em;">{key_clean}</th><th style="padding: 1rem 1.25rem; font-weight: 700; color: #ffffff; text-transform: uppercase; font-size: 1rem; letter-spacing: 0.05em;">{value}</th></tr>''')
                is_first = False
                continue

            rows.append(f'''<tr style="border-bottom: 1px solid #e2e8f0;"><td style="padding: 1rem 1.25rem; font-weight: 600; color: #1e3a8a; background: #ffffff; width: 40%; font-size: 1rem;">{key_clean}</td><td style="padding: 1rem 1.25rem; color: #25292d; font-size: 1rem; line-height: 1.7; background: #ffffff;">{value}</td></tr>''')
            is_first = False
        else:
            rows.append(f'''<tr style="border-bottom: 1px solid #f1f5f9;"><td colspan="2" style="padding: 1.1rem 1.5rem; color: #25292d; font-style: italic; background: #f8fafc; font-size: 1rem;">{clean_item}</td></tr>''')

    if not rows: return mark_safe(content)
    table_html = f'''<div class="market-coverage-wrapper" style="margin: 1rem 0 2rem 0; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; background: white;"><table style="width: 100%; border-collapse: collapse; text-align: left;"><tbody>{''.join(rows)}</tbody></table></div>'''
    return mark_safe(table_html)


@register.filter(name='format_list')
def format_list(content):
    """Convert content into bulleted list."""
    if not content: return ''
    if '<li>' in content.lower(): return mark_safe(f'<div class="tight-list-container">{content}</div>')
    lines = re.findall(r'<(?:p|h[1-6])>(.*?)</(?:p|h[1-6])>', content, re.DOTALL)
    if not lines: lines = [line.strip() for line in content.split('\n') if line.strip()]
    if not lines: return mark_safe(content)
    li_items = [f'<li style="margin-bottom: 0.4rem; color: #334155; font-weight: 500; font-size: 1.2rem;">{re.sub(r"<[^>]+>", "", line).strip()}</li>' for line in lines if line.strip()]
    if not li_items: return mark_safe(content)
    return mark_safe(f'<ul style="list-style-type: disc; padding-left: 1.5rem; margin: 1rem 0;">{"".join(li_items)}</ul>')


@register.filter(name='format_segmentation')
def format_segmentation(content):
    """Format market segmentation content. Stops at <!-- FAQ_START -->."""
    if not content: return ''
    
    # CRITICAL: Truncate at FAQ_START marker (even inside wrapper tags like <h1>)
    # The Excel importer puts FAQs in the segmentation field too
    faq_marker_match = re.search(r'(?:<[^>]*>)?\s*<!--\s*FAQ_START\s*-->', content, re.IGNORECASE)
    if faq_marker_match:
        content = content[:faq_marker_match.start()]
    
    text = re.sub(r'<(?:br|p|h[1-6]|li)[^>]*>', '\n', content)
    text = re.sub(r'</(?:p|h[1-6]|li)>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    formatted_output = []
    current_list = []
    for line in lines:
        if re.match(r'^By\s+', line, re.IGNORECASE):
            if current_list:
                formatted_output.append(f'<ul style="list-style-type: disc; padding-left: 2rem; margin-bottom: 1.5rem;">{"".join(current_list)}</ul>')
                current_list = []
            formatted_output.append(f'<div style="font-weight: 800; color: #1e3a8a; font-size: 1.3rem; margin-top: 1.8rem; margin-bottom: 0.8rem;">{line}</div>')
        else:
            current_list.append(f'<li style="margin-bottom: 0.5rem; color: #334155; font-size: 1.15rem; font-weight: 500;">{line}</li>')
    if current_list:
        formatted_output.append(f'<ul style="list-style-type: disc; padding-left: 2rem; margin-bottom: 1.5rem;">{"".join(current_list)}</ul>')
    if not formatted_output: return mark_safe(content)
    return mark_safe("".join(formatted_output))


@register.filter(name='extract_faqs_from_segmentation')
def extract_faqs_from_segmentation(content):
    """
    Extract FAQ content from the segmentation field (after <!-- FAQ_START -->).
    Used as fallback when report.faqs is empty.
    """
    if not content: return ''
    # Find FAQ_START even wrapped in tags like <h1><!-- FAQ_START --></h1>
    m = re.search(r'(?:<[^>]*>)?\s*<!--\s*FAQ_START\s*-->\s*(?:</[^>]+>)?', content, re.IGNORECASE)
    if not m: return ''
    faq_block = content[m.end():]
    # Stop at FAQ_END if present
    end_m = re.search(r'<!--\s*FAQ_END\s*-->', faq_block, re.IGNORECASE)
    if end_m: faq_block = faq_block[:end_m.start()]
    return faq_block.strip()


@register.filter(name='extract_toc_from_segmentation')
def extract_toc_from_segmentation(content):
    """
    Extract TOC content from the segmentation field (after <!-- FAQ_END -->).
    The Excel importer puts TOC as an <ol> at the very end of the segmentation field.
    """
    if not content: return ''
    # Find FAQ_END marker (TOC comes after it)
    m = re.search(r'<!--\s*FAQ_END\s*-->\s*(?:</[^>]+>)?', content, re.IGNORECASE)
    if m:
        return content[m.end():].strip()
    return ''


@register.filter(name='format_toc')
def format_toc(content):
    """
    Render raw Excel TOC HTML into a clean Chapter XX / 1.1, 1.2 styled list.
    Handles nesting level by tracking the tag depth.
    """
    if not content: return ''

    # Normalize markers for depth
    text = content
    # Chapter markers (Root-level LI frequently in H or P tags)
    text = re.sub(r'<(?:h[1-6]|p)[^>]*>\s*<li[^>]*>(.*?)(?:</(?:h[1-6]|p)>|(?=<ol)|(?=<ul>))', r'\n__CH__\1\n', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Nested item markers
    def mark_nested(m, level=1):
        inner = m.group(1)
        # Recurse for deeper nesting
        inner = re.sub(r'<ol[^>]*>(.*?)</ol>', lambda sub: mark_nested(sub, level + 1), inner, flags=re.IGNORECASE | re.DOTALL)
        # Mark current level items
        lvl_marker = f'__S{level}__'
        inner = re.sub(r'<li[^>]*>(?!\s*__CH__)(.*?)(?:</li>|(?=<ol)|(?=<ul>))', f'\n{lvl_marker}\\1\n', inner, flags=re.IGNORECASE | re.DOTALL)
        return inner
    
    text = re.sub(r'<ol[^>]*>(.*?)</ol>', lambda m: mark_nested(m, 1), text, flags=re.IGNORECASE | re.DOTALL)
    
    # Strip remaining tags
    text = re.sub(r'<[^>]+>', '', text)
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    output = []
    stack = [0, 0, 0, 0, 0] # [Chapter, S1, S2, S3, S4]

    for line in lines:
        title = line.strip()
        title = re.sub(r'[\u200b\uFEFF\xa0]+', '', title).strip()
        if not title: continue

        if '__CH__' in line:
            stack[0] += 1
            stack[1:] = [0] * (len(stack) - 1)
            clean_title = title.replace('__CH__', '').strip()
            # Don't double 'Chapter' if it's already in the text
            prefix = f'Chapter {stack[0]:02d} ' if 'chapter' not in clean_title.lower() else ''
            output.append(f'<div style="font-weight:700; color:#1e3a8a; font-size:1.3rem; margin-top:1.6rem; margin-bottom:0.3rem;">{prefix}{clean_title}</div>')
            
        elif '__S' in line:
            # Detect level from marker
            m = re.search(r'__S(\d+)__', line)
            lvl = int(m.group(1)) if m else 1
            stack[lvl] += 1
            stack[lvl+1:] = [0] * (len(stack) - lvl - 1) # Reset deeper levels
            
            clean_title = re.sub(r'__S\d+__', '', title).strip()
            # If title already starts with numbering (1.1, etc.), use it, else generate
            if re.match(r'^\d+(\.[\d\.]+)+\s', clean_title):
                num_label = ""
            else:
                parts = [str(stack[i]) for i in range(lvl + 1) if stack[i] > 0]
                num_label = ".".join(parts) + " " if parts else ""
            
            indent = 1.6 * lvl
            output.append(f'<div style="font-size:1.1rem; color:#25292d; font-weight:500; padding:0.25rem 0 0.25rem {indent}rem; line-height:1.7; font-family:\'Inter\', sans-serif;">{num_label}{clean_title}</div>')

    return mark_safe('\n'.join(output)) if output else mark_safe(content)


@register.filter(name='get_category_image_url')
def get_category_image_url(category_name):
    """Return path to category image."""
    if not category_name: return '/static/images/default_category.jpg'
    mapping = {
        'Aerospace, Defense & Security': 'Aerospace, Defense & Security.jpg',
        'Chemicals, Materials & Polymers': 'Chemicals.jpg',
        'FMCG & Consumer Products': 'FMCG.jpg',
        'Healthcare & Life Sciences': 'Healthcare.jpg',
        'Heavy Machinery & Equipment': 'Heavy Machinery.jpg',
        'Industrial Automation & Mobility': 'Industrial Automation.jpg',
        'Information Technology & Electronics': 'Information Technology.jpg',
        'Banking, Financial Services & Insurance': 'BFSI.jpg',
        'Energy & Power': 'Energy.jpg'
    }
    for k, v in mapping.items():
        if k.lower() in category_name.lower():
            return f'/static/images/{v}'
    return f'/static/images/{category_name}.jpg'


@register.filter(name='linebreak_list')
def linebreak_list(content):
    """Extract text items as list."""
    if not content: return []
    items = re.findall(r'<li[^>]*>(.*?)</li>', content, re.DOTALL)
    if not items: items = re.findall(r'<(?:p|h[1-6])[^>]*>(.*?)</(?:p|h[1-6])>', content, re.DOTALL)
    if not items:
        clean = re.sub(r'<[^>]+>', '', content)
        items = [line.strip() for line in clean.split('\n') if line.strip()]
    result = []
    for item in items:
        clean = re.sub(r'<[^>]+>', '', item).strip()
        clean = re.sub(r'^[•\-\*►▶▸→➤✓✔]\s*', '', clean).strip()
        if clean: result.append(clean)
    return result


@register.filter(name='format_highlights_box')
def format_highlights_box(content):
    """Render highlights card."""
    if not content: return ''
    items = linebreak_list(content)
    if not items: return mark_safe(content)
    items_html = ''.join(f'<li class="rh-item"><span class="rh-check">✓</span><span class="rh-text">{item}</span></li>' for item in items)
    return mark_safe(f'<div class="report-highlights-box"><div class="rh-header"><span class="rh-icon">📊</span><span class="rh-title">Report Highlights</span></div><ul class="rh-list">{items_html}</ul></div>')


def _sanitize_html(content):
    """Clean up 'tag soup' common in Excel-to-HTML exports."""
    if not content: return ''
    # 1. Strip redundant P wrapping around headings
    content = re.sub(r'<p>\s*(<h[1-6][^>]*>.*?/h[1-6]>)\s*</p>', r'\1', content, flags=re.IGNORECASE | re.DOTALL)
    
    # 2. Fix the "Heading hiding a List Item" issue (the AGC Glass fix)
    content = re.sub(r'<h([1-6])[^>]*>\s*<li>(.*?)</li>\s*</h\1>', r'<li>\2</li>', content, flags=re.IGNORECASE | re.DOTALL)
    
    # 3. Clean up P-wrapped list elements and Merge adjacent lists
    content = re.sub(r'<p>\s*(<ul[^>]*>)\s*</p>', r'\1', content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r'<p>\s*(</ul>)\s*</p>', r'\1', content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r'</ul>\s*<ul[^>]*>', '', content, flags=re.IGNORECASE) # Merge adjacent ULs
    
    # 4. Remove empty/whitespace-only headings
    def remove_ghosts(m):
        inner = m.group(2)
        if '<!--' in inner and 'IMAGE_PLACEHOLDER' in inner:
            return m.group(0)
        visible = re.sub(r'<[^>]+>', '', inner)
        visible = re.sub(r'[\u200b\uFEFF\xa0\s&nbsp;]+', '', visible).strip()
        if not visible: return ''
        return m.group(0)
    content = re.sub(r'<(h[1-6])[^>]*>(.*?)</\1>', remove_ghosts, content, flags=re.IGNORECASE | re.DOTALL)
    
    # 5. Unwrap Image Placeholders from headings (Prevents blue vertical line on maps)
    content = re.sub(r'<h[1-6][^>]*>\s*(<!--\s*IMAGE_PLACEHOLDER_\d+\s*-->)\s*</h[1-6]>', r'\1', content, flags=re.IGNORECASE | re.DOTALL)
    
    # 6. Collapse double-nested headings (e.g. <h2><h2>Text</h2></h2>)
    content = re.sub(r'<(h[1-6])[^>]*>\s*<(h\1)[^>]*>(.*?)</\2>\s*</\1>', r'<\1>\3</\1>', content, flags=re.IGNORECASE | re.DOTALL)

    return content

@register.filter(name='format_report_content')
def format_report_content(content, report_obj=None):
    """Main renderer for report description content."""
    if not content: return ''
    content = _sanitize_html(content)
    if '<h2>' in content.lower() or '<h3>' in content.lower():
        return _render_modern_format(content, report_obj, is_tab_content=False)
    return _render_legacy_format(content, report_obj)

@register.filter(name='format_tab_content')
def format_tab_content(content, report_obj=None):
    """Specialized renderer for Tab content."""
    if not content: return ''
    content = _sanitize_html(content)
    return _render_modern_format(content, report_obj, is_tab_content=True)

@register.filter(name='exclude_report_tabs')
def exclude_report_tabs(content):
    """Truncates content before TOC/Segmentation/Methodology/FAQs."""
    if not content: return ''
    # 1. Identifier Check (Primary)
    markers = [r'<!--\s*FAQ_START\s*-->', r'FAQ_START', r'TOC_START', r'SEGMENTATION_START']
    for p in markers:
        m = re.search(p, content, re.IGNORECASE)
        if m: return content[:m.start()]
    # 2. Header Check (Fallback)
    tab_keywords = ['table of content', 'market segmentation', 'methodology', 'toc', 'faq', 'q&a']
    h_pattern = re.compile(r'<h[1-6][^>]*>(.*?(?:' + '|'.join(tab_keywords) + r').*?)</h[1-6]>', re.IGNORECASE)
    h_match = h_pattern.search(content)
    if h_match: return content[:h_match.start()]
    return content


def _render_modern_format(html_content, report_obj, is_tab_content=False):
    """Handles structured HTML from Excel."""
    # Metadata
    if isinstance(report_obj, str): region, slug = report_obj, None
    elif report_obj: region, slug = getattr(report_obj, 'region', 'global'), getattr(report_obj, 'slug', None)
    else: region, slug = 'global', None
    
    # 1. Images
    html_content = html_content.replace('<!-- IMAGE_PLACEHOLDER_1 -->', _render_bar_chart(slug))
    
    # Only show regional map for Global reports
    if region and 'global' in region.lower():
        html_content = html_content.replace('<!-- IMAGE_PLACEHOLDER_2 -->', _render_regional_map(region, slug))
    else:
        # Remove placeholder for country reports
        html_content = html_content.replace('<!-- IMAGE_PLACEHOLDER_2 -->', '')
        
    html_content = html_content.replace('<!-- IMAGE_PLACEHOLDER_3 -->', _render_deck(slug))

    # 2. Highlights
    h_pat = re.compile(r'<h[1-6][^>]*>(.*?Highlight.*?)</h[1-6]>\s*<ul[^>]*>(.*?)</ul>', re.IGNORECASE | re.DOTALL)
    def h_repl(m): return _render_report_highlights([i.strip() for i in re.findall(r'<li>(.*?)</li>', m.group(2), re.DOTALL) if i.strip()], m.group(1).strip())
    html_content = h_pat.sub(h_repl, html_content)

    # 3. Market Coverage / Tables
    t_pat = re.compile(r'<h[1-6][^>]*>(.*?Market.*?|.*?Coverage.*?)</h[1-6]>\s*<table[^>]*>(.*?)</table>', re.IGNORECASE | re.DOTALL)
    def t_repl(m):
        raw_rows = re.findall(r'<tr>(.*?)</tr>', m.group(2), re.DOTALL)
        line_data = []
        for r in raw_rows:
            cols = re.findall(r'<t[dh]>(.*?)</t[dh]>', r, re.DOTALL)
            if len(cols) >= 2: line_data.append(f"{cols[0].strip()} | {cols[1].strip()}")
        rendered = _render_market_coverage_table(line_data)
        if is_tab_content: return f'<h2 style="color:#1e3a8a; font-weight:700; margin-top:2rem;">{m.group(1).strip()}</h2>{rendered}'
        return f'<h1 class="section-header">{m.group(1).strip()}</h1>{rendered}'
    html_content = t_pat.sub(t_repl, html_content)

    # 4. Standard Headings
    # Refined Check: Section markers to prevent company names items from becoming headers
    SECTION_KEYWORDS = ['insight', 'segment', 'geography', 'region', 'forecast', 'product', 'type', 'end-use', 'industry', 'overview', 'summary', 'highlight', 'marker', 'players', 'participants', 'dynamics', 'timeline', 'case', 'bull', 'bear', 'analysis', 'methodology', 'contents', 'table']
    
    def hr(m):
        txt = m.group(1).strip()
        clean = re.sub(r'[\u200b\uFEFF\xa0\s]+', '', re.sub(r'<[^>]+>', '', txt)).strip()
        if not clean: return ''
        # Logic: If it's a short item without section keywords, it's probably a participant or list item
        if is_tab_content and len(clean) < 45 and not any(kw in clean.lower() for kw in SECTION_KEYWORDS):
             return f'<div style="margin: 0.5rem 0 0.5rem 1.5rem; color:#475569;">• {txt}</div>'
        if is_tab_content: return f'<h2 style="color:#1e3a8a; font-weight:700; margin-top:1.5rem; margin-bottom:0.8rem;">{txt}</h2>'
        return f'<h1 class="section-header">{txt}</h1>'
    html_content = re.sub(r'<h2[^>]*>(.*?)</h2>', hr, html_content, flags=re.IGNORECASE | re.DOTALL)

    def shr(m):
        txt = m.group(1).strip()
        clean = re.sub(r'[\u200b\uFEFF\xa0\s]+', '', re.sub(r'<[^>]+>', '', txt)).strip()
        if not clean: return ''
        if is_tab_content and len(clean) < 45 and not any(kw in clean.lower() for kw in SECTION_KEYWORDS):
             return f'<div style="margin: 0.5rem 0 0.5rem 1.5rem; color:#475569;">• {txt}</div>'
        if is_tab_content: return f'<h3 style="color:#334155; font-weight:600; margin-top:1rem; margin-left:1rem;">{txt}</h3>'
        return f'<h2 class="section-subheader" style="border-left:4px solid #3b82f6; padding-left:1rem;">{txt}</h2>'
    html_content = re.sub(r'<h3[^>]*>(.*?)</h3>', shr, html_content, flags=re.IGNORECASE | re.DOTALL)

    return mark_safe(html_content)


@register.filter(name='extract_section')
def extract_section(content, section_name):
    """Robust extractor for FAQ, TOC, Segmentation."""
    if not content: return ''
    keyword = section_name.lower().strip()

    # 1. FAQ Marker Extraction
    if 'faq' in keyword:
        m = re.search(r'<!--\s*(?:FAQ|QUESTIONS)?_?START\s*-->(.*?)<!--\s*(?:FAQ|QUESTIONS)?_?END\s*-->', content, re.IGNORECASE | re.DOTALL)
        if not m: m = re.search(r'<!--\s*(?:FAQ|QUESTIONS)?_?START\s*-->(.*)', content, re.IGNORECASE | re.DOTALL)
        if m: return mark_safe(m.group(1).strip())

    # 2. TOC Fallback Extraction (Last List)
    if any(k in keyword for k in ['toc', 'table of contents']):
        lists = list(re.finditer(r'<(ol|ul)[^>]*>(.*?)</\1>', content, re.IGNORECASE | re.DOTALL))
        if lists:
            for m in reversed(lists):
                if len(re.findall(r'<li>', m.group(0))) > 5: return mark_safe(m.group(0))

    # 3. Dynamic Section Extraction (Line by Line)
    content = _sanitize_html(content)
    text = re.sub(r'<h([1-6])[^>]*>(.*?)</h\1>', r'\n###H\1###\2###HEND###\n', content, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<(?:p|br)[^>]*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<(?!/?(?:li|ul|ol|strong|b|em|i|a|span|table|tr|td|th|!)[>\s])[^>]+>', '', text)
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    HEADING_MARKER = re.compile(r'###H([1-6])###(.*?)###HEND###', re.IGNORECASE)
    aliases = {'segmentation': ['segments', 'market segmentation', 'break down', 'by product', 'by application']}
    targets = [keyword] + aliases.get(keyword, [])
    
    si = -1
    for idx, ln in enumerate(lines):
        hm = HEADING_MARKER.search(ln)
        if hm and any(t in hm.group(2).lower() for t in targets): si = idx; break
        # Plain text header check
        if 0 < len(ln.split()) <= 6 and any(t in ln.lower() for t in targets) and not ':' in ln: si = idx; break
            
    if si == -1: return ''
    
    sl = []
    break_words = ['faq', 'question', 'toc', 'contents', 'methodology', 'summary', 'highlight']
    if keyword != 'faq': break_words.extend(['FAQ_START', 'FAQ_END'])
    qs_list = ('what', 'how', 'why', 'who', 'when', 'where', 'is', 'are', 'which', 'can', 'do', 'does')

    for i in range(si, len(lines)):
        ln = lines[i]
        if keyword != 'faq' and any(m in ln.upper() for m in ['FAQ_START', 'TOC_START']): break
        if keyword == 'segmentation':
            if any(re.sub(r'<[^>]+>|###H[1-6]###|###HEND###', '', ln).lower().strip().startswith(qs) for qs in qs_list): break

        hm = HEADING_MARKER.search(ln)
        if hm and i > si:
            ht = hm.group(2).lower()
            if any(bw in ht for bw in break_words):
                if keyword == 'segmentation' and any(s in ht for s in (aliases['segmentation'] + ['by geography'])): pass
                else: break
                    
        sl.append(re.sub(r'###HEND###', '</h2>', re.sub(r'###H[1-6]###', '<h2>', ln)))
        
    return mark_safe('\n'.join(sl))


def _render_legacy_format(content, report_obj):
    """Old format logic."""
    # (Simplified legacy logic to keep the file size manageable)
    return mark_safe(content)


def _render_bar_chart(slug):
    """Bar chart card — Image 1 (after Report Highlights)."""
    url = f'/reports/request-sample/{slug}/' if slug else '#'
    try:
        url = reverse('request-sample', kwargs={'slug': slug}) if slug else '#'
    except: pass
    return f'''
<div style="text-align: center; margin: 2.5rem 0 0.75rem 0;">
    <div style="background:#fff; border-radius:16px; box-shadow:0 4px 24px rgba(0,0,0,0.08); display:inline-block; padding:0; overflow:hidden; max-width:92%;">
        <img src="/static/images/reports/bar_chart_standard.jpg" alt="Market Growth Chart"
             style="max-width:100%; display:block; border-radius:16px;">
    </div>
</div>
<div style="text-align:center; margin-bottom:2.5rem; font-size:0.97rem; font-weight:500; color:#334155;">
    Want Detailed Insights - <a href="{url}" style="color:#2563eb; text-decoration:underline;">Download Sample</a>
</div>'''

def _render_regional_map(region, slug):
    """Regional map card — Image 2 (mid content)."""
    url = f'/reports/ask-for-discount/{slug}/' if slug else '#'
    try:
        url = reverse('ask-for-discount', kwargs={'slug': slug}) if slug else '#'
    except: pass
    return f'''
<div style="text-align: center; margin: 2.5rem 0 0.75rem 0;">
    <div style="background:#fff; border-radius:16px; box-shadow:0 4px 24px rgba(0,0,0,0.08); display:inline-block; padding:0; overflow:hidden; max-width:92%;">
        <img src="/static/images/reports/regional_map_standard.png" alt="Regional Market Map"
             style="max-width:100%; display:block; border-radius:16px;">
    </div>
</div>
<div style="text-align:center; margin-bottom:2.5rem; font-size:0.97rem; font-weight:500; color:#334155;">
    Limited Budget ? - <a href="{url}" style="color:#2563eb; text-decoration:underline;">Ask for Discount</a>
</div>'''

def _render_deck(slug):
    """Deck preview card — Image 3 (end of content)."""
    url = f'/reports/request-customization/{slug}/' if slug else '#'
    try:
        url = reverse('request-customization', kwargs={'slug': slug}) if slug else '#'
    except: pass
    return f'''
<div style="text-align: center; margin: 2.5rem 0 0.75rem 0;">
    <div style="background:#fff; border-radius:16px; box-shadow:0 4px 24px rgba(0,0,0,0.08); display:inline-block; padding:0; overflow:hidden; max-width:92%;">
        <img src="/static/images/reports/deck_standard.jpg" alt="Market Analysis Dashboard"
             style="max-width:100%; display:block; border-radius:16px;">
    </div>
</div>
<div style="text-align:center; margin-bottom:2.5rem; font-size:0.97rem; font-weight:500; color:#334155;">
    Need Customized Scope - <a href="{url}" style="color:#2563eb; text-decoration:underline;">Get my Report Customized</a>
</div>'''

def _render_market_coverage_table(line_data):
    """Professional table renderer."""
    rows = []
    for line in line_data:
        if '|' in line:
            k, v = line.split('|', 1)
            rows.append(f'<tr style="border-bottom: 1px solid #f1f5f9;"><td style="padding: 1rem; font-weight: 700; color: #1e3a8a; width: 35%; background: #f8fafc; font-size: 1rem;">{k.strip()}</td><td style="padding: 1rem; color: #25292d; font-size: 1rem; line-height: 1.7;">{v.strip()}</td></tr>')
    return f'<div style="margin: 2rem 0; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;"><table style="width: 100%; border-collapse: collapse;"><tbody>{"".join(rows)}</tbody></table></div>'

def _render_report_highlights(items, h_text="Report Highlights"):
    """Premium Highlights box."""
    lis = "".join(f'<li style="display: flex; gap: 0.5rem; padding: 0.2rem 0;"><span style="color: #10b981;">✓</span><span style="color: #1e293b; font-weight: 500;">{i}</span></li>' for i in items)
    return f'<h1 class="section-header">{h_text}</h1><div style="background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); border-left: 6px solid #1e3a8a; padding: 1.5rem 2rem; border-radius: 12px; margin: 2rem 0; box-shadow: 0 4px 10px rgba(0,0,0,0.05);"><ul style="list-style: none; padding: 0; margin: 0;">{lis}</ul></div>'
