#!/usr/bin/env python3

import re

def extract_customers_from_jql(jql_file_path):
    """
    Extract customer names from a JQL query file.
    Parses the 'customers[select list (multiple choices)]' IN clause.
    
    Args:
        jql_file_path: Path to JQL query file
    
    Returns:
        List of customer names
    """
    try:
        with open(jql_file_path, 'r') as f:
            jql_content = f.read()
        
        # Look for the customers IN clause
        # Pattern: "customers[...]" IN ("Customer1", Customer2, "Customer3")
        pattern = r'"customers\[select list \(multiple choices\)\]"\s+IN\s+\((.*?)\)(?:\s+AND|\s+ORDER|$)'
        match = re.search(pattern, jql_content, re.IGNORECASE | re.DOTALL)
        
        if not match:
            return []
        
        customers_str = match.group(1)
        
        # Use a smarter approach: split by comma, but respect quoted strings
        customers = []
        current = ""
        in_quotes = False
        
        for char in customers_str:
            if char == '"':
                in_quotes = not in_quotes
            elif char == ',' and not in_quotes:
                # End of current customer
                customer = current.strip().strip('"').strip()
                if customer and customer.upper() not in ['AND', 'OR', 'IN', 'NOT']:
                    customers.append(customer)
                current = ""
            else:
                current += char
        
        # Don't forget the last one
        customer = current.strip().strip('"').strip()
        if customer and customer.upper() not in ['AND', 'OR', 'IN', 'NOT']:
            customers.append(customer)
        
        return customers
        
    except FileNotFoundError:
        print(f"Warning: JQL file not found: {jql_file_path}")
        return []
    except Exception as e:
        print(f"Warning: Error parsing JQL file: {e}")
        return []

if __name__ == '__main__':
    # Test with PS query file
    customers = extract_customers_from_jql('config/jql_ps_query.txt')
    print(f"Found {len(customers)} customers:")
    for customer in customers:
        print(f"  - {customer}")
