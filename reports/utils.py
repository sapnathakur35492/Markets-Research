"""
Utility functions for the reports app
"""
import re
from django.utils.text import slugify


def auto_format_content(text):
    """
    Auto-format plain text content with HTML tags.
    
    Rules:
    - All uppercase lines (< 100 chars) → H1
    - Lines ending with colon (< 100 chars) → H2
    - Lines starting with numbers (e.g., "1. Introduction") → H3
    - Everything else → <p> tags
    
    Args:
        text (str): Plain text content from Excel/ChatGPT
        
    Returns:
        str: HTML-formatted content
    """
    if not text:
        return ''
    
    lines = text.split('\n')
    formatted_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        clean_text = line.replace('**', '').replace('*', '').strip()
        
        # Apply bold/italic to the text for inclusion in tags
        styled_line = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', line)
        styled_line = re.sub(r'\*(.*?)\*', r'<em>\1</em>', styled_line)
        
        # H1: All uppercase clean_text
        if clean_text.isupper() and len(clean_text) < 100 and not clean_text.startswith('-'):
            formatted_lines.append(f'<h1>{clean_text}</h1>')
        
        # H2: Clean text ends with colon
        elif clean_text.endswith(':') and len(clean_text) < 100:
            # Strip colon that might be followed by markdown markers
            line_no_colon = re.sub(r':\s*([\*]*)$', r'\1', line)
            styled_h2 = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', line_no_colon)
            styled_h2 = re.sub(r'\*(.*?)\*', r'<em>\1</em>', styled_h2)
            formatted_lines.append(f'<h2>{styled_h2}</h2>')
            
        # H3: Numbered sections
        elif re.match(r'^\d+\.', clean_text):
            formatted_lines.append(f'<h3>{styled_line}</h3>')
            
        # List items
        elif line.startswith('-') or line.startswith('•'):
            # Strip the marker and apply styling to the rest
            item_content = line[1:].strip()
            item_styled = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', item_content)
            item_styled = re.sub(r'\*(.*?)\*', r'<em>\1</em>', item_styled)
            formatted_lines.append(f'<li>{item_styled}</li>')
            
        # Regular paragraph
        else:
            formatted_lines.append(f'<p>{styled_line}</p>')
    
    # Wrap consecutive <li> tags in <ul>
    processed_html = []
    in_list = False
    
    for line in formatted_lines:
        if line.startswith('<li>'):
            if not in_list:
                processed_html.append('<ul>')
                in_list = True
            processed_html.append(line)
        else:
            if in_list:
                processed_html.append('</ul>')
                in_list = False
            processed_html.append(line)
    
    if in_list:
        processed_html.append('</ul>')
            
    return '\n'.join(processed_html)


def parse_content_sections(content):
    """
    Parse content and extract different sections based on headings.
    Also extracts TOC structure and Segmentation chapters separately.
    
    Args:
        content (str): Full HTML-formatted content from Excel
        
    Returns:
        dict: Dictionary with:
            - 'sections': dict with section names as keys and content as values
            - 'toc': TOC structure content (from "Table of Contents" heading)
            - 'segmentation': Segmentation chapters content (from segmentation-related headings)
            - 'cleaned_summary': Summary with TOC and Segmentation removed
    """
    if not content:
        return {
            'sections': {},
            'toc': '',
            'segmentation': '',
            'cleaned_summary': ''
        }
    
    # Define section headings to look for (case-insensitive)
    section_patterns = {
        'report_highlights': r'(?i)<p>Report Highlights</p>',
        'industry_snapshot': r'(?i)<p>Industry Snapshot</p>',
        'market_growth_catalysts': r'(?i)<p>Key Market Growth Catalysts</p>',
        'market_challenges': r'(?i)<p>Market Challenges and Constraints</p>',
        'strategic_opportunities': r'(?i)<p>Strategic Growth Opportunities</p>',
        'market_coverage': r'(?i)<p>Market Coverage Overview</p>',
        'geographic_analysis': r'(?i)<p>Geographic Performance Analysis</p>',
        'competitive_environment': r'(?i)<p>Competitive Environment Analysis</p>',
        'leading_participants': r'(?i)<p>Leading Market Participants</p>',
        'long_term_perspective': r'(?i)<p>Long-Term Market Perspective</p>',
    }
    
    sections = {}
    
    # Extract the 10 named sections
    for field_name, pattern in section_patterns.items():
        match = re.search(pattern, content)
        if match:
            start_pos = match.end()
            
            # Find the next section heading (including FAQ, Chapter, Segmentation, Methodology to prevent them from being included in sections)
            remaining_content = content[start_pos:]
            # Improved regex to handle both <p> and <h> tags for all section headings
            next_heading_pattern = r'(?i)(?:<p>|<[ph][1-6]?>)(?:Report Highlights|Industry Snapshot|Key Market Growth Catalysts|Market Challenges and Constraints|Strategic Growth Opportunities|Market Coverage Overview|Geographic Performance Analysis|Competitive Environment Analysis|Leading Market Participants|Long-Term Market Perspective|Frequently Asked Questions|FAQ[s]?|Market Segmentation|Segmentation|Methodology|Chapter \d+)'
            next_heading = re.search(next_heading_pattern, remaining_content)
            
            if next_heading:
                section_content = remaining_content[:next_heading.start()].strip()
            else:
                section_content = remaining_content.strip()
            
            sections[field_name] = section_content
    
    # Extract TOC content - extract all chapter headings and their subsections
    # The TOC is the chapter structure (Chapter 01, 02, 03, etc. with subsections)
    toc_content = ''
    
    # Find all chapter headings and their subsections
    chapter_pattern = r'<p>Chapter \d+.*?</p>(?:.*?(?=<p>Chapter \d+|<p>Market Segmentation|$))'
    chapters = re.findall(chapter_pattern, content, re.DOTALL | re.IGNORECASE)
    
    if chapters:
        # Build TOC from chapter headings
        toc_parts = []
        for chapter in chapters:
            # Extract just the chapter heading and its immediate subsections (h3 tags)
            chapter_heading = re.search(r'<p>(Chapter \d+.*?)</p>', chapter)
            if chapter_heading:
                toc_parts.append(f'<p>{chapter_heading.group(1)}</p>')
                
                # Extract subsections (h3 tags) within this chapter
                subsections = re.findall(r'<h3>(.*?)</h3>', chapter)
                for subsection in subsections[:10]:  # Limit to first 10 subsections per chapter
                    toc_parts.append(f'<h3>{subsection}</h3>')
        
        toc_content = '\n'.join(toc_parts)
    
    # Alternative: Look for explicit "Table of Contents" heading
    if not toc_content:
        toc_patterns = [
            r'(?i)<[ph][1-6]?>Table\s+of\s+Contents</[ph][1-6]?>',
            r'(?i)<p>Table\s+of\s+Contents</p>',
            r'(?i)<p>TOC</p>',
        ]
        
        toc_start = None
        for pattern in toc_patterns:
            toc_match = re.search(pattern, content)
            if toc_match:
                toc_start = toc_match.start()
                break
        
        if toc_start is not None:
            # Find where TOC ends - look for the next major heading
            toc_end_patterns = [
                r'(?i)<[ph][1-6]?>(?:Market\s+)?Segmentation</[ph][1-6]?>',
                r'(?i)<p>(?:Market\s+)?Segmentation</p>',
                r'(?i)<[ph][1-6]?>Methodology</[ph][1-6]?>',
                r'(?i)<p>Methodology</p>',
                r'(?i)<[ph][1-6]?>Chapter\s+\d+',
                r'(?i)<p>Chapter\s+\d+',
                r'(?i)<[ph][1-6]?>FAQ',
                r'(?i)<p>FAQ',
            ]
            
            toc_end = None
            remaining_after_toc = content[toc_start:]
            
            # Skip the TOC heading itself and look for the next heading
            first_heading_end = re.search(r'</[ph][1-6]?>|</p>', remaining_after_toc)
            if first_heading_end:
                search_start = first_heading_end.end()
                for pattern in toc_end_patterns:
                    end_match = re.search(pattern, remaining_after_toc[search_start:])
                    if end_match:
                        toc_end = toc_start + search_start + end_match.start()
                        break
            
            if toc_end:
                # Extract content AFTER the heading
                toc_content = content[toc_start + search_start:toc_end].strip() if first_heading_end else content[toc_start:toc_end].strip()
            else:
                # If no end found, take a reasonable amount after heading
                toc_content = remaining_after_toc[search_start:2000].strip() if first_heading_end else remaining_after_toc[:2000].strip()
    
    # Extract Segmentation content - look for "Segmentation" or "Market Segmentation" heading
    segmentation_content = ''
    seg_patterns = [
        r'(?i)<[ph][1-6]?>(?:Market\s+)?Segmentation</[ph][1-6]?>',
        r'(?i)<p>(?:Market\s+)?Segmentation</p>',
    ]
    
    seg_start = None
    for pattern in seg_patterns:
        seg_match = re.search(pattern, content)
        if seg_match:
            seg_start = seg_match.start()
            break
    
    if seg_start is not None:
        # Find where Segmentation ends - look for next major heading
        seg_end_patterns = [
            r'(?i)<[ph][1-6]?>Methodology',
            r'(?i)<p>Methodology',
            r'(?i)<[ph][1-6]?>FAQ',
            r'(?i)<p>FAQ',
            r'(?i)<[ph][1-6]?>Frequently\s+Asked',
            r'(?i)<p>Frequently\s+Asked',
        ]
        
        seg_end = None
        remaining_after_seg = content[seg_start:]
        
        # Skip the Segmentation heading itself (template will add styled H2 heading)
        first_heading_end = re.search(r'</[ph][1-6]?>|</p>', remaining_after_seg)
        if first_heading_end:
            search_start = first_heading_end.end()
            for pattern in seg_end_patterns:
                end_match = re.search(pattern, remaining_after_seg[search_start:])
                if end_match:
                    seg_end = seg_start + search_start + end_match.start()
                    break
        
        if seg_end:
            # Extract content AFTER the heading
            segmentation_content = content[seg_start + search_start:seg_end].strip()
        else:
            # If no end found, take everything after segmentation heading
            segmentation_content = remaining_after_seg[search_start:].strip() if first_heading_end else remaining_after_seg.strip()
    
    # Extract FAQs content - look for "Frequently Asked Questions" or "FAQ" heading
    faqs_content = ''
    faq_patterns = [
        r'(?i)<[ph][1-6]?>Frequently\s+Asked\s+Questions</[ph][1-6]?>',
        r'(?i)<p>Frequently\s+Asked\s+Questions</p>',
        r'(?i)<[ph][1-6]?>FAQ[s]?</[ph][1-6]?>',
        r'(?i)<p>FAQ[s]?</p>',
        r'(?i)<[ph][1-6]?>Report\s+FAQ[s]?</[ph][1-6]?>',
        r'(?i)<p>Report\s+FAQ[s]?</p>',
    ]
    
    faq_start = None
    for pattern in faq_patterns:
        faq_match = re.search(pattern, content)
        if faq_match:
            faq_start = faq_match.start()
            break
    
    if faq_start is not None:
        # FAQs are typically at the end
        faq_end_patterns = [
            r'(?i)<[ph][1-6]?>Table\s+of\s+Contents',
            r'(?i)<p>Table\s+of\s+Contents',
            r'(?i)<[ph][1-6]?>Chapter\s+\d+',
            r'(?i)<p>Chapter\s+\d+',
        ]
        
        remaining_after_faq = content[faq_start:]
        
        # Skip the FAQ heading itself (template will add styled H2 heading)
        first_heading_end = re.search(r'</[ph][1-6]?>|</p>', remaining_after_faq)
        if first_heading_end:
            search_start = first_heading_end.end()
            faq_end = None
            for pattern in faq_end_patterns:
                end_match = re.search(pattern, remaining_after_faq[search_start:])
                if end_match:
                    faq_end = faq_start + search_start + end_match.start()
                    break
            
            if faq_end:
                # Extract content AFTER the heading
                faqs_content = content[faq_start + search_start:faq_end].strip()
            else:
                # If no end found, take everything after FAQ heading
                faqs_content = remaining_after_faq[search_start:].strip()
    
    # Create cleaned summary by removing chapters, TOC, Segmentation, and FAQs
    # The summary should only contain the 10 named content sections
    cleaned_summary = content
    
    # Remove all chapters (Chapter 01, 02, 03, etc.) from summary
    chapter_removal_pattern = r'(?i)(?:<p>|<[ph][1-6]?>)Chapter \d+.*?(?:</p>|</[ph][1-6]?>).*?(?=(?:<p>|<[ph][1-6]?>)(?:Chapter \d+|Report Highlights|Industry Snapshot|Key Market Growth Catalysts|Market Challenges|Strategic Growth Opportunities|Market Coverage|Geographic Performance|Competitive Environment|Leading Market Participants|Long-Term Market Perspective|Frequently Asked|Market Segmentation|Methodology)|$)'
    cleaned_summary = re.sub(chapter_removal_pattern, '', cleaned_summary, flags=re.DOTALL)
    
    # Remove explicit "Table of Contents" heading section if found
    cleaned_summary = re.sub(r'(?i)(?:<p>|<[ph][1-6]?>)Table\s+of\s+Contents(?:</p>|</[ph][1-6]?>).*?(?=(?:<p>|<[ph][1-6]?>)(?:Chapter\s+\d+|Report Highlights)|$)', '', cleaned_summary, flags=re.DOTALL)

    # Remove Segmentation section from summary
    cleaned_summary = re.sub(r'(?i)(?:<p>|<[ph][1-6]?>)(?:Market\s+)?Segmentation(?:</p>|</[ph][1-6]?>).*?(?=(?:<p>|<[ph][1-6]?>)(?:Methodology|Frequently Asked|Chapter \d+)|$)', '', cleaned_summary, flags=re.DOTALL)
    
    # Remove FAQs section from summary
    cleaned_summary = re.sub(r'(?i)(?:<p>|<[ph][1-6]?>)Frequently\s+Asked\s+Questions(?:</p>|</[ph][1-6]?>).*?$', '', cleaned_summary, flags=re.DOTALL)
    cleaned_summary = re.sub(r'(?i)(?:<p>|<[ph][1-6]?>)FAQ[s]?(?:</p>|</[ph][1-6]?>).*?$', '', cleaned_summary, flags=re.DOTALL)
    
    cleaned_summary = cleaned_summary.strip()
    
    return {
        'sections': sections,
        'toc': toc_content,
        'segmentation': segmentation_content,
        'faqs': faqs_content,
        'cleaned_summary': cleaned_summary
    }


def generate_slug_from_title(title):
    """
    Generate URL-safe slug from title.
    
    Args:
        title (str): Report title
        
    Returns:
        str: URL-safe slug
    """
    return slugify(title)

