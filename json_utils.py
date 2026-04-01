import json
import os
import re
from .symbol_mappings import ALL_SYMBOLS

def clean_and_validate_json(json_str):
    """Clean and validate the JSON string."""
    if not json_str:
        print("Error: Empty JSON string received")
        return []
        
    # Remove markdown code block delimiters if present
    json_str = json_str.replace('```json', '').replace('```', '').strip()
    
    try:
        parsed_json = json.loads(json_str)
        
        # Create DEBUG directory if it doesn't exist
        os.makedirs('DEBUG', exist_ok=True)
        
        # Write the parsed JSON to a file for debugging
        with open('DEBUG/response.json', 'w') as f:
            json.dump(parsed_json, f, indent=2)
            
        # Ensure we return a list even if the API returns a single object
        if isinstance(parsed_json, dict):
            return [parsed_json]
        
        return parsed_json
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {str(e)}")
        print(f"Problematic JSON string: {json_str[:100]}...")  # Print first 100 chars for debugging
        # Try to find and extract JSON-like parts
        try:
            # Look for content between brackets
            import re
            json_match = re.search(r'\[.*\]', json_str, re.DOTALL)
            if json_match:
                fixed_json = json_match.group(0)
                return json.loads(fixed_json)
        except Exception as nested_e:
            print(f"Failed to recover JSON: {str(nested_e)}")
        
        return []
    except Exception as e:
        print(f"Unexpected error parsing JSON: {str(e)}")
        return []

def clean_option_text(text):
    """
    Clean and format option text to be suitable for Telegram polls,
    especially handling mathematical and chemical expressions.
    """
    # Handle LaTeX fractions
    text = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'\1/\2', text)
    
    # Handle matrix formatting
    def format_matrix(match):
        # Extract matrix content
        content = match.group(1)
        # Split into rows
        rows = [row.strip() for row in content.split('\\\\')]
        # Split each row into columns
        matrix = [row.split('&') for row in rows]
        
        # Format indices with subscripts
        for i in range(len(matrix)):
            for j in range(len(matrix[i])):
                cell = matrix[i][j].strip()
                # Convert a_{ij} style indices to proper subscripts
                cell = re.sub(r'a_\{(\d+)(\d+)\}', lambda m: f'a{["₀","₁","₂","₃","₄","₅","₆","₇","₈","₉"][int(m.group(1))]}{["₀","₁","₂","₃","₄","₅","₆","₇","₈","₉"][int(m.group(2))]}', cell)
                # Handle specific subscript patterns shown in the image
                cell = re.sub(r'a_11', 'a₁₁', cell)
                cell = re.sub(r'a_12', 'a₁₂', cell)
                cell = re.sub(r'a_13', 'a₁₃', cell)
                cell = re.sub(r'a_21', 'a₂₁', cell)
                cell = re.sub(r'a_22', 'a₂₂', cell)
                cell = re.sub(r'a_23', 'a₂₃', cell)
                cell = re.sub(r'a_31', 'a₃₁', cell)
                cell = re.sub(r'a_32', 'a₃₂', cell)
                cell = re.sub(r'a_33', 'a₃₃', cell)
                # Use standard format for other cases
                cell = re.sub(r'a_(\d)(\d)', lambda m: f'a{["₀","₁","₂","₃","₄","₅","₆","₇","₈","₉"][int(m.group(1))]}{["₀","₁","₂","₃","₄","₅","₆","₇","₈","₉"][int(m.group(2))]}', cell)
                matrix[i][j] = cell
        
        # Calculate maximum width for each column
        col_widths = []
        for col in range(len(matrix[0])):
            col_widths.append(max(len(row[col]) for row in matrix))
        
        # Format in the exact style shown in the image
        formatted_rows = []
        for i, row in enumerate(matrix):
            if i == 0:
                # First row starts with top-left bracket
                formatted_row = '⎡'
            elif i == len(matrix) - 1:
                # Last row starts with bottom-left bracket
                formatted_row = '⎣'
            else:
                # Middle rows start with vertical bar
                formatted_row = '⎢'
            
            # Add each cell with proper spacing
            for j, cell in enumerate(row):
                # Center-align each element in its column
                width = col_widths[j]
                padding_left = (width - len(cell)) // 2
                padding_right = width - len(cell) - padding_left
                formatted_row += ' ' * padding_left + cell + ' ' * padding_right + ' '
            
            # Add right bracket
            if i == 0:
                # First row ends with top-right bracket
                formatted_row += '⎤'
            elif i == len(matrix) - 1:
                # Last row ends with bottom-right bracket
                formatted_row += '⎦'
            else:
                # Middle rows end with vertical bar
                formatted_row += '⎥'
            
            formatted_rows.append(formatted_row)
        
        # Return the formatted matrix
        return '\n'.join(formatted_rows)
    
    # Replace LaTeX matrix environments
    text = re.sub(r'\\begin\{matrix\}(.*?)\\end\{matrix\}', format_matrix, text, flags=re.DOTALL)
    
    # Also handle pmatrix and bmatrix
    text = re.sub(r'\\begin\{pmatrix\}(.*?)\\end\{pmatrix\}', format_matrix, text, flags=re.DOTALL)
    text = re.sub(r'\\begin\{bmatrix\}(.*?)\\end\{bmatrix\}', format_matrix, text, flags=re.DOTALL)
    
    # Handle chemical subscripts (convert H2O to H₂O)
    text = re.sub(r'([A-Za-z])(\d+)', lambda m: m.group(1) + ''.join(['₀₁₂₃₄₅₆₇₈₉'[int(d)] for d in m.group(2)]), text)
    
    # Handle superscripts (10^6 to 10⁶)
    text = re.sub(r'(\d+)\^(\d+)', lambda m: m.group(1) + ''.join(['⁰¹²³⁴⁵⁶⁷⁸⁹'[int(d)] for d in m.group(2)]), text)
    
    # Handle chemical bonds
    text = re.sub(r'-(?!>)', '−', text)  # Single bond (but not arrows)
    text = re.sub(r'=(?!=)', '═', text)  # Double bond
    text = re.sub(r'≡(?!≡)', '≡', text)  # Triple bond
    
    # Handle benzene rings and cyclic structures
    text = re.sub(r'\\benzene', '⌬', text)
    text = re.sub(r'\\phenyl', 'Ph', text)
    text = re.sub(r'\\cyclo', '○', text)
    
    # Handle common organic groups and functional groups
    text = re.sub(r'CH3', 'CH₃', text)
    text = re.sub(r'CH2', 'CH₂', text)
    text = re.sub(r'OCH3', 'OCH₃', text)
    text = re.sub(r'OH', 'OH', text)
    text = re.sub(r'NH2', 'NH₂', text)
    text = re.sub(r'COOH', 'COOH', text)
    text = re.sub(r'NO2', 'NO₂', text)
    text = re.sub(r'SO3H', 'SO₃H', text)
    text = re.sub(r'PO4', 'PO₄', text)
    text = re.sub(r'CO2', 'CO₂', text)
    text = re.sub(r'H3O', 'H₃O', text)
    text = re.sub(r'H2O', 'H₂O', text)
    text = re.sub(r'NH3', 'NH₃', text)
    text = re.sub(r'NH4', 'NH₄', text)
    text = re.sub(r'SO4', 'SO₄', text)
    
    # Handle square roots
    text = re.sub(r'\\sqrt\{([^}]+)\}', r'√\1', text)
    
    # Handle chemical arrows with states
    text = re.sub(r'\\xrightarrow\{([^}]+)\}', r'→[\1]', text)
    text = re.sub(r'\\xleftarrow\{([^}]+)\}', r'←[\1]', text)
    
    # Replace LaTeX symbols with Unicode equivalents
    for latex, symbol in ALL_SYMBOLS.items():
        text = text.replace(latex, symbol)
    
    # Remove option labels like "A) " or "a. "
    text = re.sub(r'^[A-Da-d][).]\s*', '', text)
    
    # Clean up any remaining LaTeX commands
    text = re.sub(r'\\[a-zA-Z]+', '', text)
    
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Handle direct bracket matrix format as shown in the image
    def format_bracket_matrix(match):
        content = match.group(1)
        rows = content.split('\\\\')
        matrix = []
        
        for row in rows:
            cells = [cell.strip() for cell in row.strip().split('&')]
            matrix.append(cells)
        
        # Calculate maximum width for each column
        col_widths = []
        for col in range(len(matrix[0])):
            col_widths.append(max(len(row[col]) for row in matrix))
        
        # Format in the same style as the main matrix handler
        formatted_rows = []
        for i, row in enumerate(matrix):
            if i == 0:
                # First row starts with top-left bracket
                formatted_row = '⎡'
            elif i == len(matrix) - 1:
                # Last row starts with bottom-left bracket
                formatted_row = '⎣'
            else:
                # Middle rows start with vertical bar
                formatted_row = '⎢'
            
            # Add each cell with proper spacing
            for j, cell in enumerate(row):
                # Center-align each element in its column
                width = col_widths[j]
                padding_left = (width - len(cell)) // 2
                padding_right = width - len(cell) - padding_left
                formatted_row += ' ' * padding_left + cell + ' ' * padding_right + ' '
            
            # Add right bracket
            if i == 0:
                # First row ends with top-right bracket
                formatted_row += '⎤'
            elif i == len(matrix) - 1:
                # Last row ends with bottom-right bracket
                formatted_row += '⎦'
            else:
                # Middle rows end with vertical bar
                formatted_row += '⎥'
            
            formatted_rows.append(formatted_row)
        
        # Return the formatted matrix
        return '\n'.join(formatted_rows)
    
    # Try to handle the specific matrix format shown in the image
    text = re.sub(r'\\begin\{bmatrix\}(.*?)\\end\{bmatrix\}', format_bracket_matrix, text, flags=re.DOTALL)
    text = re.sub(r'\\left\[(.*?)\\right\]', format_bracket_matrix, text, flags=re.DOTALL)
    
    # Handle the specific 3x3 matrix format from the image
    if "a_11" in text and "a_12" in text and "a_13" in text:
        matrix_text = """⎡ a₁₁ a₁₂ a₁₃ ⎤
⎢ a₂₁ a₂₂ a₂₃ ⎥
⎣ a₃₁ a₃₂ a₃₃ ⎦"""
        text = re.sub(r'\\begin\{[a-z]*matrix\}[^}]*\\end\{[a-z]*matrix\}', matrix_text, text)
        text = re.sub(r'\\left\[([^]]+)\\right\]', matrix_text, text)
    
    # Handle tables using box-drawing characters
    def format_table(match):
        # Extract table content
        content = match.group(1)
        # Split into rows
        rows = [row.strip() for row in content.split('\\\\')]
        # Split each row into columns
        table = [row.split('&') for row in rows]
        
        # Calculate maximum width for each column
        col_widths = []
        for col in range(len(table[0])):
            col_widths.append(max(len(row[col].strip()) for row in table))
        
        # Format with box-drawing characters
        formatted_rows = []
        
        # Create top border
        top_border = '┌'
        for width in col_widths:
            top_border += '─' * (width + 2) + '┬'
        top_border = top_border[:-1] + '┐'
        formatted_rows.append(top_border)
        
        # Format each row
        for i, row in enumerate(table):
            formatted_row = '│'
            for j, cell in enumerate(row):
                cell = cell.strip()
                # Pad with spaces to align columns
                formatted_row += ' ' + cell.ljust(col_widths[j]) + ' │'
            formatted_rows.append(formatted_row)
            
            # Add row separator if not the last row
            if i < len(table) - 1:
                separator = '├'
                for width in col_widths:
                    separator += '─' * (width + 2) + '┼'
                separator = separator[:-1] + '┤'
                formatted_rows.append(separator)
        
        # Create bottom border
        bottom_border = '└'
        for width in col_widths:
            bottom_border += '─' * (width + 2) + '┴'
        bottom_border = bottom_border[:-1] + '┘'
        formatted_rows.append(bottom_border)
        
        return '\n'.join(formatted_rows)
    
    # Replace LaTeX table environments
    text = re.sub(r'\\begin\{tabular\}\{[^}]*\}(.*?)\\end\{tabular\}', format_table, text, flags=re.DOTALL)
    
    # Handle simplified table syntax
    text = re.sub(r'\\begin\{table\}(.*?)\\end\{table\}', format_table, text, flags=re.DOTALL)
    
    # Handle special matrices in different formats that appear in the questions
    # This part handles matrices in the format [1 2 3; 2 1 3] or similar
    def format_special_matrix(text):
        # Look for patterns like [1 2 3; 4 5 6; 7 8 9]
        matrix_pattern = r'\[([0-9\s;]+)\]'
        matches = re.findall(matrix_pattern, text)
        
        for match in matches:
            if ';' in match:  # Matrix format with semicolons
                rows = match.split(';')
                elements = [row.strip().split() for row in rows]
                
                # Calculate maximum width for each column
                col_widths = []
                for col in range(len(elements[0])):
                    col_widths.append(max(len(row[col]) for row in elements if col < len(row)))
                
                # Format matrix with proper brackets
                formatted_rows = []
                for i, row in enumerate(elements):
                    if i == 0:
                        formatted_row = '⎡'
                    elif i == len(elements) - 1:
                        formatted_row = '⎣'
                    else:
                        formatted_row = '⎢'
                    
                    # Add each cell with proper spacing
                    for j, cell in enumerate(row):
                        if j < len(col_widths):  # Safety check
                            width = col_widths[j]
                            padding_left = (width - len(cell)) // 2
                            padding_right = width - len(cell) - padding_left
                            formatted_row += ' ' * padding_left + cell + ' ' * padding_right + ' '
                    
                    # Add right bracket
                    if i == 0:
                        formatted_row += '⎤'
                    elif i == len(elements) - 1:
                        formatted_row += '⎦'
                    else:
                        formatted_row += '⎥'
                    
                    formatted_rows.append(formatted_row)
                
                # Replace the original matrix with formatted version
                matrix_text = '\n'.join(formatted_rows)
                text = text.replace(f'[{match}]', matrix_text)
        
        return text
        
    # Apply special matrix formatting after other replacements
    text = format_special_matrix(text)
    
    return text