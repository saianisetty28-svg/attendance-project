from salesforce_connection import sf

result = sf.query(
    """
    SELECT Id,
           Name,
           Email
    FROM Contact
    LIMIT 5
    """
)

print(result)