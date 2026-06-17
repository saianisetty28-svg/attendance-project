import os
import requests
from simple_salesforce import Salesforce

SF_USERNAME = "deekshadas2002.b8953bf2b61f@agentforce.com"
SF_PASSWORD = "deeksha@123"
SF_SECURITY_TOKEN = "3vmE0GCJL2cJbvlQG9zSOENI9"

CACHE_DIR = r"C:\Users\pranav h r\attendance_system\cache\employee_images"


def get_sf():
    return Salesforce(
        username=SF_USERNAME,
        password=SF_PASSWORD,
        security_token=SF_SECURITY_TOKEN
    )


def chunked(sequence, size):
    for i in range(0, len(sequence), size):
        yield sequence[i:i + size]


def sync_employees():

    sf = get_sf()

    contacts = sf.query_all("""
        SELECT Id,
               Name,
               Employee__c
        FROM Contact
        WHERE Employee__c != NULL
    """)

    records = contacts.get("records", [])
    num_contacts = len(records)
    print(f"Found {num_contacts} contact(s) with Employee__c")

    if num_contacts == 0:
        return

    contact_map = {
        contact["Id"]: {
            "employee_id": contact["Employee__c"],
            "name": contact.get("Name")
        }
        for contact in records
    }

    contact_ids = list(contact_map.keys())
    print(f"Loading ContentDocumentLink records for {len(contact_ids)} contacts")

    content_links = []
    for chunk in chunked(contact_ids, 200):
        ids_list = ",".join(f"'{contact_id}'" for contact_id in chunk)
        links = sf.query_all(f"""
            SELECT ContentDocumentId,
                   LinkedEntityId
            FROM ContentDocumentLink
            WHERE LinkedEntityId IN ({ids_list})
        """)
        content_links.extend(links.get("records", []))

    print(f"Found {len(content_links)} ContentDocumentLink record(s)")
    if not content_links:
        return

    content_document_ids = [link["ContentDocumentId"] for link in content_links if link.get("ContentDocumentId")]
    unique_content_ids = list(dict.fromkeys(content_document_ids))

    print(f"Loading latest ContentVersion for {len(unique_content_ids)} documents")

    version_records = []
    for chunk in chunked(unique_content_ids, 200):
        ids_list = ",".join(f"'{doc_id}'" for doc_id in chunk)
        versions = sf.query_all(f"""
            SELECT Id,
                   ContentDocumentId,
                   Title,
                   VersionData
            FROM ContentVersion
            WHERE ContentDocumentId IN ({ids_list})
            ORDER BY ContentDocumentId, CreatedDate DESC
        """)
        version_records.extend(versions.get("records", []))

    latest_versions = {}
    for version in version_records:
        doc_id = version["ContentDocumentId"]
        if doc_id not in latest_versions:
            latest_versions[doc_id] = version

    links_by_contact = {}
    for link in content_links:
        contact_id = link.get("LinkedEntityId")
        doc_id = link.get("ContentDocumentId")
        if not contact_id or not doc_id:
            continue
        links_by_contact.setdefault(contact_id, []).append(doc_id)

    session_id = sf.session_id
    instance = sf.sf_instance

    for contact_id, contact_info in contact_map.items():
        employee_id = contact_info["employee_id"]
        contact_name = contact_info["name"]

        document_ids = links_by_contact.get(contact_id, [])
        print(f"Processing contact {contact_name} ({contact_id}) -> employee {employee_id}")
        print(f"  Found {len(document_ids)} linked file(s)")

        employee_folder = os.path.join(CACHE_DIR, employee_id)
        os.makedirs(employee_folder, exist_ok=True)

        saved_count = 0
        for doc_id in document_ids:
            if saved_count >= 5:
                break

            version = latest_versions.get(doc_id)
            if not version:
                print(f"  No ContentVersion found for document {doc_id}")
                continue

            version_id = version.get("Id")
            title = version.get("Title") or doc_id
            version_data = version.get("VersionData")
            if not version_data:
                print(f"  No VersionData for ContentVersion {version_id}")
                continue

            ext = os.path.splitext(title)[1] or ".jpg"
            file_name = f"img{saved_count + 1}{ext}"
            url = f"https://{instance}{version_data}"

            headers = {"Authorization": f"Bearer {session_id}"}
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code != 200:
                print(f"  Failed to download ContentVersion {version_id}: {response.status_code}")
                continue

            save_path = os.path.join(employee_folder, file_name)
            with open(save_path, "wb") as f:
                f.write(response.content)

            print(f"  Saved {file_name} from document {title} ({doc_id})")
            saved_count += 1

        if saved_count == 0:
            print(f"  No files synced for contact {contact_id}")
        else:
            print(f"  Synced {saved_count} file(s) for employee {employee_id}")

if __name__ == "__main__":
    sync_employees()