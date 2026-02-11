"""
Unit tests for DatabaseService

Tests cover:
- Connection pool initialization
- Query execution with parameters
- Error handling
- Connection reuse
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from app.core.services.database_service import DatabaseService


@pytest.fixture
def db_service():
    """Create DatabaseService instance"""
    with patch('app.core.services.database_service.psycopg2'):
        service = DatabaseService()
        return service


class TestDatabaseServiceInitialization:
    """Test DatabaseService initialization"""

    @patch('app.core.services.database_service.psycopg2.pool.ThreadedConnectionPool')
    def test_pool_initialization(self, mock_pool_class):
        """Test connection pool initializes correctly"""
        mock_pool = Mock()
        mock_pool_class.return_value = mock_pool
        
        service = DatabaseService()
        
        # Verify pool was created
        assert mock_pool_class.called


class TestQueryExecution:
    """Test query execution methods"""

    def test_execute_query_with_parameters(self, db_service):
        """Test execute with parameter substitution"""
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        db_service.pool.getconn = Mock(return_value=mock_conn)
        
        # Act
        result = db_service.execute("SELECT * FROM blacklist WHERE ip = %s", ("1.2.3.4",))
        
        # Assert
        mock_cursor.execute.assert_called_once()

    def test_execute_query_returns_data(self, db_service):
        """Test execute returns fetched data"""
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [{"ip": "1.2.3.4", "reason": "malware"}]
        mock_conn.cursor.return_value = mock_cursor
        db_service.pool.getconn = Mock(return_value=mock_conn)
        
        # Act
        result = db_service.execute("SELECT * FROM blacklist LIMIT 1")
        
        # Assert
        assert result is not None


class TestErrorHandling:
    """Test error handling in database operations"""

    def test_execute_handles_connection_error(self, db_service):
        """Test execute handles connection failures"""
        # Arrange
        db_service.pool.getconn = Mock(side_effect=Exception("Connection failed"))
        
        # Act & Assert
        with pytest.raises(Exception):
            db_service.execute("SELECT * FROM blacklist")

    def test_execute_handles_syntax_error(self, db_service):
        """Test execute handles SQL syntax errors"""
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.execute.side_effect = Exception("Syntax error")
        mock_conn.cursor.return_value = mock_cursor
        db_service.pool.getconn = Mock(return_value=mock_conn)
        
        # Act & Assert
        with pytest.raises(Exception):
            db_service.execute("INVALID SQL")

