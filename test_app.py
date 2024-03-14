import os
import tempfile
import pytest
from app import app, db, Paste
from datetime import datetime

@pytest.fixture
def client():
    db_fd, db_path = tempfile.mkstemp()
    app.config['SQLALCHEMY_DATABASE_URI'] =  'sqlite:///:memory:'#'sqlite:///' + db_path
    app.config['TESTING'] = True

    with app.app_context():
        db.create_all()
    
    yield app.test_client()

    os.close(db_fd)
    os.unlink(db_path)

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

    
# def test_create_paste(client):
#     with app.app_context():
#         """Test creating a new paste."""
#         test_title = '123'
#         test_content = '456'
#         response = client.post('/', data={'title': test_title, 'content': test_content}, follow_redirects=True)
#         assert response.status_code == 200
#         assert bytes(test_title, 'utf-8') in response.data
#         assert bytes(test_content, 'utf-8') in response.data
#         print("++++")
#         print(response.data)

#         # # Debug: Print the first paste entry to verify
#         paste = Paste.query.first()
#         print(f"Debug - Title: {paste.title}, Content: {paste.content}")

#         # assert paste is not None
#         # assert paste.title == test_title
#         # assert paste.content == test_content

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
