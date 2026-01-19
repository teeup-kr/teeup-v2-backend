from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import pymysql
from config import settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create SQLAlchemy engine
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
    # echo=settings.ENVIRONMENT == "development"
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_connection():
    """Test database connection"""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            logger.info("Database connection successful")
            return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

def create_database_if_not_exists():
    """Create database if it doesn't exist"""
    try:
        # Parse DATABASE_URL to extract components
        from urllib.parse import urlparse
        parsed_url = urlparse(settings.DATABASE_URL)
        
        # Connect without specifying database
        temp_url = f"mysql+pymysql://{parsed_url.username}:{parsed_url.password}@{parsed_url.hostname}:{parsed_url.port}"
        temp_engine = create_engine(temp_url)
        
        with temp_engine.connect() as connection:
            # Check if database exists
            db_name = parsed_url.path.lstrip('/')
            result = connection.execute(text(f"SHOW DATABASES LIKE '{db_name}'"))
            if not result.fetchone():
                # Create database
                connection.execute(text(f"CREATE DATABASE {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                logger.info(f"Database '{db_name}' created successfully")
            else:
                logger.info(f"Database '{db_name}' already exists")
        
        temp_engine.dispose()
        return True
    except Exception as e:
        logger.error(f"Failed to create database: {e}")
        return False

def init_database():
    """Initialize database connection and create tables"""
    # Create database if not exists
    if not create_database_if_not_exists():
        return False
    
    # Test connection
    if not test_connection():
        return False
    
    # Create tables automatically (베스트 프렉티스: 개발 환경에서만 자동 생성)
    # 프로덕션 환경에서는 환경 변수 AUTO_CREATE_TABLES=true로 명시적으로 설정해야 함
    auto_create = settings.AUTO_CREATE_TABLES
    
    # 환경 변수가 명시적으로 설정되지 않은 경우, 개발 환경에서만 자동 생성
    if auto_create is None:
        auto_create = settings.ENVIRONMENT == "development"
    
    if auto_create:
        try:
            # Lazy import to avoid circular dependencies
            # 모듈을 import하면 모든 모델이 로드되어 Base.metadata에 등록됨
            import models  # noqa: F401
            
            # 테이블 생성 (기존 테이블이 있어도 에러 없이 처리됨)
            logger.info("Creating database tables...")
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created/verified successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            # 테이블 생성 실패해도 서버는 시작하도록 함 (기존 테이블이 있을 수 있음)
            logger.warning("Continuing server startup despite table creation error")
    else:
        logger.info("Auto table creation is disabled (set AUTO_CREATE_TABLES=true to enable)")
    
    logger.info("Database initialization completed successfully")
    return True