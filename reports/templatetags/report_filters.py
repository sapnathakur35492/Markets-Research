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
    Convert FAQ HTML into styled accordion cards.
    Splits on h2/h3 headings (questions) and captures everything between them as answer.
    Handles both <h3>Q</h3><p>A</p> and plain-text answers without p tags.
    """
    if not faq_content:
        return ''

    # Strategy 1: Split on h2/h3 tags — each heading is a question,
    # everything up to the next heading is the answer.
    parts = re.split(r'(<h[23][^>]*>.*?</h[23]>)', faq_content, flags=re.DOTALL | re.IGNORECASE)

    qa_pairs = []
    i = 0
    while i < len(parts):
        chunk = parts[i].strip()
        if re.match(r'<h[23]', chunk, re.IGNORECASE):
            question = re.sub(r'<[^>]+>', '', chunk).strip()
            # Answer is everything in the next non-heading chunk
            answer_raw = parts[i + 1].strip() if i + 1 < len(parts) else ''
            # Strip inner p tags but keep text
            answer = re.sub(r'</?p[^>]*>', ' ', answer_raw, flags=re.IGNORECASE).strip()
            answer = re.sub(r'<[^>]+>', '', answer).strip()
            if question:
                qa_pairs.append((question, answer))
            i += 2
        else:
            i += 1

    # Strategy 2: fallback — extract p tags as Q-A pairs (ends with ?)
    if not qa_pairs:
        paragraphs = re.findall(r'<(?:p|h[1-6]|li)[^>]*>(.*?)</(?:p|h[1-6]|li)>', faq_content, re.DOTALL)
        cleaned = []
        for p in paragraphs:
            text = re.sub(r'<[^>]+>', '', p).strip()
            text = re.sub(r'[\u200b\uFEFF\xa0]+', ' ', text).strip()
            if text:
                cleaned.append(text)

        j = 0
        while j < len(cleaned):
            para = cleaned[j]
            is_q = para.strip().endswith('?') or bool(re.match(r'^Q\d+[\.\s]', para, re.IGNORECASE))
            if is_q:
                question = re.sub(r'^(Q\d+|Question\s*\d*)\s*[:.]?\s*', '', para, flags=re.IGNORECASE).strip()
                answer = cleaned[j + 1] if j + 1 < len(cleaned) else ''
                qa_pairs.append((question, answer))
                j += 2
            else:
                j += 1

    if not qa_pairs:
        return mark_safe(faq_content)

    faq_cards = []
    for idx, (question, answer) in enumerate(qa_pairs, 1):
        faq_cards.append(f'''
<div class="faq-accordion-item">
    <button class="faq-accordion-header" type="button">
        <span class="faq-question-text"><span class="q-num">Q{idx}.</span> {question}</span>
        <span class="faq-arrow">▼</span>
    </button>
    <div class="faq-accordion-content">
        <div class="faq-answer-inner">{answer}</div>
    </div>
</div>''')

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
    
    # Remove redundant "Market Segmentation" title if it exists at the start
    if lines and lines[0].lower() == 'market segmentation':
        lines = lines[1:]

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
    
    toc_match = re.search(r'<!--\s*TOC_START\s*-->(.*?)<!--\s*TOC_END\s*-->', content, re.IGNORECASE | re.DOTALL)
    if toc_match:
        return toc_match.group(1).strip()
        
    # Find FAQ_END marker (TOC comes after it)
    m = re.search(r'<!--\s*FAQ_END\s*-->\s*(?:</[^>]+>)?', content, re.IGNORECASE)
    if m:
        return content[m.end():].strip()
    return ''


@register.filter(name='format_toc')
def format_toc(content):
    """
    Render TOC HTML with Chapter XX headings and 1.1/1.2 numbered sub-items.
    Handles both new format (everything inside outer <ol>) and legacy format
    (chapters as loose p/h tags, sub-items in nested <ol>).
    """
    if not content:
        return ''

    # Strip TOC markers
    content = re.sub(r'<!--\s*TOC_START\s*-->', '', content, flags=re.IGNORECASE)
    content = re.sub(r'<!--\s*TOC_END\s*-->', '', content, flags=re.IGNORECASE)

    # Strip the h2 "Table of Contents" heading — the template already shows the tab title
    content = re.sub(r'<h[1-6][^>]*>\s*Table\s+of\s+Contents\s*</h[1-6]>', '', content, flags=re.IGNORECASE)

    output = []
    ch_count = 0
    sub_counters = [0] * 6   # sub_counters[depth] for depth 2,3,4...

    # Tokenize into list tags and text
    tokens = re.split(r'(</?(?:ol|ul|li)[^>]*>)', content, flags=re.IGNORECASE)

    depth = 0        # current list nesting depth (1 = outermost ol)
    in_li = False
    li_depth = 0
    li_text_parts = []

    def flush_li(li_d, text):
        """Emit a formatted line for a completed <li> at depth li_d."""
        nonlocal ch_count
        raw = re.sub(r'<[^>]+>', '', text).strip()
        raw = re.sub(r'[\u200b\uFEFF\xa0]+', ' ', raw).strip()
        if not raw:
            return

        if li_d == 1:
            # Top-level → Chapter heading
            ch_count += 1
            # Reset all sub counters
            for i in range(len(sub_counters)):
                sub_counters[i] = 0
            prefix = f'Chapter {ch_count:02d} ' if not raw.lower().startswith('chapter') else ''
            output.append(
                f'<div style="font-weight:700; color:#1e3a8a; font-size:1.2rem;'
                f' margin-top:1.4rem; margin-bottom:0.2rem;">{prefix}{raw}</div>'
            )
        else:
            # Sub-item at depth li_d (2 = first sub-level, 3 = second, etc.)
            idx = li_d - 2   # index into sub_counters
            if idx < 0: idx = 0
            sub_counters[idx] += 1
            # Reset deeper counters
            for i in range(idx + 1, len(sub_counters)):
                sub_counters[i] = 0

            # Build numeric label: e.g. "3.2 " for chapter 3, sub-item 2
            if idx == 0:
                num_label = f'{ch_count}.{sub_counters[0]} '
            elif idx == 1:
                num_label = f'{ch_count}.{sub_counters[0]}.{sub_counters[1]} '
            else:
                parts = [str(ch_count)] + [str(sub_counters[i]) for i in range(idx + 1)]
                num_label = '.'.join(parts) + ' '

            # If title already starts with a number like "3.2", don't double-add
            if re.match(r'^\d+(\.\d+)+\s', raw):
                num_label = ''

            indent = 1.6 * (li_d - 1)
            output.append(
                f'<div style="font-size:1rem; color:#25292d; font-weight:500;'
                f' padding:0.15rem 0 0.15rem {indent}rem; line-height:1.75;'
                f' font-family:\'Inter\', sans-serif;">{num_label}{raw}</div>'
            )

    for token in tokens:
        if not token:
            continue
        tag = re.match(r'<(/?)(ol|ul|li)([^>]*)>', token, re.IGNORECASE)
        if tag:
            closing, name, _ = tag.group(1), tag.group(2).lower(), tag.group(3)
            if name in ('ol', 'ul'):
                if closing:
                    depth = max(0, depth - 1)
                else:
                    depth += 1
            elif name == 'li':
                if closing:
                    if in_li:
                        flush_li(li_depth, ''.join(li_text_parts))
                        li_text_parts = []
                        in_li = False
                else:
                    if in_li:
                        # Unclosed li — flush previous
                        flush_li(li_depth, ''.join(li_text_parts))
                        li_text_parts = []
                    in_li = True
                    li_depth = depth
        else:
            if in_li:
                li_text_parts.append(token)

    # Flush any trailing unclosed li
    if in_li and li_text_parts:
        flush_li(li_depth, ''.join(li_text_parts))

    return mark_safe('\n'.join(output)) if output else mark_safe(content)



@register.filter(name='get_category_image_url')
def get_category_image_url(category_name):
    """Return path to category image."""
    from urllib.parse import quote
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
    # Normalize: replace "and" with "&" so both forms match
    normalized_name = category_name.lower().replace(' and ', ' & ')
    for k, v in mapping.items():
        if k.lower() in normalized_name:
            return f'/static/images/{quote(v)}'
    return f'/static/images/{quote(category_name + ".jpg")}'


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
    markers = [
        r'<!--\s*FAQ_START\s*-->', 
        r'FAQ_START', 
        r'TOC_START', 
        r'SEGMENTATION_START',
        r'SEGMENT_START',
        r'SEGMENTATION_END',
        r'SEGMENT_END'
    ]
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

    # 1. Segmentation Marker Extraction (New)
    if 'segmentation' in keyword:
        m = re.search(r'<!--\s*SEGMENT(?:ATION)?_?START\s*-->(.*?)<!--\s*SEGMENT(?:ATION)?_?END\s*-->', content, re.IGNORECASE | re.DOTALL)
        if m: return mark_safe(m.group(1).strip())

    # 2. FAQ Marker Extraction
    if 'faq' in keyword:
        m = re.search(r'<!--\s*(?:FAQ|QUESTIONS)?_?START\s*-->(.*?)<!--\s*(?:FAQ|QUESTIONS)?_?END\s*-->', content, re.IGNORECASE | re.DOTALL)
        if not m: m = re.search(r'<!--\s*(?:FAQ|QUESTIONS)?_?START\s*-->(.*)', content, re.IGNORECASE | re.DOTALL)
        if m: return mark_safe(m.group(1).strip())

    # 3. TOC Marker and Fallback Extraction (Last List)
    if any(k in keyword for k in ['toc', 'table of contents']):
        m = re.search(r'<!--\s*TOC_START\s*-->(.*?)<!--\s*TOC_END\s*-->', content, re.IGNORECASE | re.DOTALL)
        if m: return mark_safe(m.group(1).strip())
        
        lists = list(re.finditer(r'<(ol|ul)[^>]*>(.*?)</\1>', content, re.IGNORECASE | re.DOTALL))
        if lists:
            for m in reversed(lists):
                if len(re.findall(r'<li>', m.group(0))) > 5: return mark_safe(m.group(0))

    # 4. Dynamic Section Extraction (Line by Line)
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
