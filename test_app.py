import os
import tempfile
import pytest
from app import app, db, Paste, generate_key, decrypt_content, encrypt_content
from datetime import datetime

@pytest.fixture
def client():
    db_fd, db_path = tempfile.mkstemp()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # Use in-memory database for tests
    app.config['TESTING'] = True

    with app.app_context():
        db.create_all()
    
    test_client = app.test_client()

    yield test_client

    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def example_paste(client):
    """Fixture to create an example paste that can be used in multiple tests."""
    with app.app_context():
        paste = Paste(title='Encrypted Test', content=encrypt_content('This is a test.', 'test_password'), is_encrypted=True)
        paste.set_password('test_password')
        db.session.add(paste)
        db.session.commit()
    return paste

# def test_encryption_decryption(client, example_paste):
#     """Test encryption and decryption of paste content."""
#     with app.app_context():

#         response = client.post('/', data={'title': 'testing_title', 'content': 'testing_content', 'encrypt': 'on', 'password': 'test_assword'}, follow_redirects=True)


#                 # Inside your encryption test or function
#         print("Encryption Key:", generate_key('test_password'))

#         # Inside your decryption test or function, for the same password
#         print("Decryption Key:", generate_key('test_password'))

#         paste = Paste.query.filter_by(title='testing_title').first()
#         assert paste is not None, "The encrypted paste object was not found in the database."
        
#         # Decrypt the content directly for testing
#         decrypted_content = decrypt_content(paste.content, 'test_password')
#         assert decrypted_content == 'testing_content', "Direct decryption with the correct password failed."
        
#         # Since decryption is tested directly above, ensure your application logic 
#         # and session handling also support displaying decrypted content correctly.

def test_encryption_key_consistency():
    """Test that the encryption key generated from a password is consistent."""
    password = "test_password"
    key1 = generate_key(password)
    key2 = generate_key(password)
    assert key1 == key2, "Generated encryption keys from the same password should be identical."

def test_paste_encryption(client):
    """Test creating an encrypted paste and its decryption."""
    test_title = 'Encrypted Paste'
    test_content = 'Secret content'
    password = 'encryption_test_password'
    response = client.post('/', data={'title': test_title, 'content': test_content, 'encrypt': 'on', 'password': password}, follow_redirects=True)
    assert response.status_code == 200, "Failed to create an encrypted paste."
    
    with app.app_context():
        paste = Paste.query.filter_by(title=test_title).first()
        assert paste is not None, "The encrypted paste was not found in the database."
        assert paste.is_encrypted, "The paste was not marked as encrypted."
        
        # Directly decrypt the content for verification
        decrypted_content = decrypt_content(paste.content, password)
        assert decrypted_content == test_content, "Decryption of the paste content failed."

def test_index_get(client):
    """Test retrieving the index page."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Submit a new Paste' in response.data  # Adjust based on your index.html content

def test_create_paste(client):
    with app.app_context():
        test_title = '123'
        test_content = '456'
        response = client.post('/', data={'title': test_title, 'content': test_content}, follow_redirects=True)
        assert response.status_code == 200
        
        # Query specifically for the paste created by this test
        paste = Paste.query.filter_by(title=test_title, content=test_content).first()
        
        assert paste is not None, "The paste object was not found in the database."
        assert paste.title == test_title, f"Expected title {test_title}, got {paste.title}"
        assert paste.content == test_content, f"Expected content {test_content}, got {paste.content}"



def test_paste_view(client):
    with app.app_context():
        """Test viewing an individual paste."""
        # Create a paste to view
        paste = Paste(title='View Test', content='Content for viewing test', timestamp=datetime.utcnow())
        db.session.add(paste)
        db.session.commit()

        response = client.get(f'/p/{paste.uuid}')
        assert response.status_code == 200
        assert b'View Test' in response.data
        assert b'Content for viewing test' in response.data

def test_404_page(client):
    """Test 404 error handler."""
    response = client.get('/nothinghere')
    assert response.status_code == 404
    assert b"We can't seem to find the page you're looking for: 404" in response.data 

