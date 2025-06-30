"""
Migration system for Finviz Stock Scraper.
Handles migration from file-based storage (JSON/CSV) to SQLite database.
"""
import json
import csv
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from config.database_config import (
    get_migration_backup_path,
    ensure_migration_backup_directory,
    MIGRATION_CONFIG
)
from src.database.database_manager import DatabaseManager

logger = logging.getLogger(__name__)

class MigrationManager:
    """Manages migration from file-based storage to SQLite database."""
    
    def __init__(self, database_manager: DatabaseManager):
        """Initialize the migration manager.
        
        Args:
            database_manager: Database manager instance
        """
        self.db_manager = database_manager
        self.migration_backup_path = get_migration_backup_path()
        ensure_migration_backup_directory()
    
    def detect_existing_data(self) -> Dict[str, Any]:
        """Detect existing file-based data that can be migrated.
        
        Returns:
            Dictionary with information about existing data files
        """
        base_path = Path(__file__).parent.parent.parent
        data_info = {
            'urls_json_exists': False,
            'urls_json_path': None,
            'csv_files_exist': False,
            'csv_files': [],
            'migration_needed': False
        }
        
        # Check for URLs JSON file
        urls_json_path = base_path / 'data' / 'urls.json'
        if urls_json_path.exists():
            data_info['urls_json_exists'] = True
            data_info['urls_json_path'] = str(urls_json_path)
            data_info['migration_needed'] = True
        
        # Check for CSV files in results directory
        results_dir = base_path / 'data' / 'results'
        if results_dir.exists():
            csv_files = list(results_dir.glob('*.csv'))
            if csv_files:
                data_info['csv_files_exist'] = True
                data_info['csv_files'] = [str(f) for f in csv_files]
                data_info['migration_needed'] = True
        
        return data_info
    
    def create_backup(self, file_path: str) -> str:
        """Create a backup of a file before migration.
        
        Args:
            file_path: Path to the file to backup
            
        Returns:
            Path to the backup file
        """
        try:
            file_path_obj = Path(file_path)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"{file_path_obj.stem}_{timestamp}{file_path_obj.suffix}"
            backup_path = self.migration_backup_path / backup_filename
            
            shutil.copy2(file_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Error creating backup for {file_path}: {e}")
            raise
    
    def migrate_urls_from_json(self, json_file_path: str) -> bool:
        """Migrate URLs from JSON file to SQLite database.
        
        Args:
            json_file_path: Path to the JSON file containing URLs
            
        Returns:
            True if migration was successful, False otherwise
        """
        try:
            # Create backup
            if MIGRATION_CONFIG['backup_before_migration']:
                self.create_backup(json_file_path)
            
            # Read JSON data
            with open(json_file_path, 'r') as f:
                urls_data = json.load(f)
            
            if not isinstance(urls_data, dict):
                logger.error("Invalid JSON format: expected dictionary")
                return False
            
            # Migrate URLs to database
            migrated_count = 0
            for name, url in urls_data.items():
                try:
                    # Check if URL already exists
                    existing = self.db_manager.execute_query(
                        "SELECT id FROM urls WHERE name = ?",
                        (name,)
                    )
                    
                    if not existing:
                        # Insert new URL
                        self.db_manager.execute_update(
                            "INSERT INTO urls (name, url) VALUES (?, ?)",
                            (name, url)
                        )
                        migrated_count += 1
                        logger.debug(f"Migrated URL: {name}")
                    else:
                        logger.debug(f"URL already exists: {name}")
                        
                except Exception as e:
                    logger.error(f"Error migrating URL {name}: {e}")
                    continue
            
            logger.info(f"Successfully migrated {migrated_count} URLs from JSON")
            return True
            
        except Exception as e:
            logger.error(f"Error migrating URLs from JSON: {e}")
            return False
    
    def migrate_tickers_from_csv(self, csv_file_path: str) -> bool:
        """Migrate ticker data from CSV file to SQLite database.
        
        Args:
            csv_file_path: Path to the CSV file containing ticker data
            
        Returns:
            True if migration was successful, False otherwise
        """
        try:
            # Create backup
            if MIGRATION_CONFIG['backup_before_migration']:
                self.create_backup(csv_file_path)
            
            csv_path = Path(csv_file_path)
            url_name = csv_path.stem  # Use filename as URL name
            
            # Get URL ID from database
            url_result = self.db_manager.execute_query(
                "SELECT id FROM urls WHERE name = ?",
                (url_name,)
            )
            
            if not url_result:
                logger.warning(f"URL '{url_name}' not found in database, skipping CSV migration")
                return False
            
            url_id = url_result[0][0]
            
            # Create scraping session
            session_result = self.db_manager.execute_update(
                "INSERT INTO scraping_sessions (url_id, status, ticker_count) VALUES (?, ?, ?)",
                (url_id, 'completed', 0)
            )
            
            if not session_result:
                logger.error("Failed to create scraping session")
                return False
            
            # Get session ID
            session_id = self.db_manager.execute_query(
                "SELECT last_insert_rowid()"
            )[0][0]
            
            # Read CSV and migrate tickers
            migrated_count = 0
            ticker_data = []
            
            with open(csv_file_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    ticker_symbol = row.get('ticker_symbol', '').strip()
                    if ticker_symbol:
                        ticker_data.append((session_id, ticker_symbol))
                        migrated_count += 1
            
            # Batch insert tickers
            if ticker_data:
                self.db_manager.execute_many(
                    "INSERT INTO ticker_results (session_id, ticker_symbol) VALUES (?, ?)",
                    ticker_data
                )
                
                # Update session ticker count
                self.db_manager.execute_update(
                    "UPDATE scraping_sessions SET ticker_count = ? WHERE id = ?",
                    (migrated_count, session_id)
                )
            
            logger.info(f"Successfully migrated {migrated_count} tickers from CSV: {csv_file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error migrating tickers from CSV {csv_file_path}: {e}")
            return False
    
    def migrate_schema_for_deduplication(self):
        """Add deduplication fields to scraping_sessions if they do not exist."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                # Add content_hash column if missing
                cursor.execute("PRAGMA table_info(scraping_sessions)")
                columns = [row[1] for row in cursor.fetchall()]
                if 'content_hash' not in columns:
                    cursor.execute("ALTER TABLE scraping_sessions ADD COLUMN content_hash TEXT")
                if 'dedup_reason' not in columns:
                    cursor.execute("ALTER TABLE scraping_sessions ADD COLUMN dedup_reason TEXT")
                conn.commit()
                logger.info("Migration: deduplication fields ensured in scraping_sessions table.")
                return True
        except Exception as e:
            logger.error(f"Error migrating schema for deduplication: {e}")
            return False
    
    def verify_migration(self, original_data_info: Dict[str, Any]) -> Dict[str, Any]:
        """Verify that migration was successful by comparing data.
        
        Args:
            original_data_info: Information about original data files
            
        Returns:
            Dictionary with verification results
        """
        verification_results = {
            'urls_migrated': 0,
            'urls_expected': 0,
            'tickers_migrated': 0,
            'tickers_expected': 0,
            'verification_passed': False
        }
        
        try:
            # Verify URLs migration
            if original_data_info['urls_json_exists']:
                # Count URLs in JSON file
                with open(original_data_info['urls_json_path'], 'r') as f:
                    urls_data = json.load(f)
                    verification_results['urls_expected'] = len(urls_data)
                
                # Count URLs in database
                db_urls = self.db_manager.execute_query("SELECT COUNT(*) FROM urls")
                verification_results['urls_migrated'] = db_urls[0][0]
            
            # Verify tickers migration
            if original_data_info['csv_files_exist']:
                total_tickers_expected = 0
                total_tickers_migrated = 0
                
                # Count tickers in CSV files
                for csv_file in original_data_info['csv_files']:
                    with open(csv_file, 'r', newline='', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        ticker_count = sum(1 for row in reader if row.get('ticker_symbol', '').strip())
                        total_tickers_expected += ticker_count
                
                # Count tickers in database
                db_tickers = self.db_manager.execute_query("SELECT COUNT(*) FROM ticker_results")
                total_tickers_migrated = db_tickers[0][0]
                
                verification_results['tickers_expected'] = total_tickers_expected
                verification_results['tickers_migrated'] = total_tickers_migrated
            
            # Check if verification passed
            urls_match = verification_results['urls_migrated'] == verification_results['urls_expected']
            tickers_match = verification_results['tickers_migrated'] == verification_results['tickers_expected']
            verification_results['verification_passed'] = urls_match and tickers_match
            
            logger.info(f"Migration verification: URLs {verification_results['urls_migrated']}/{verification_results['urls_expected']}, "
                       f"Tickers {verification_results['tickers_migrated']}/{verification_results['tickers_expected']}")
            
            return verification_results
            
        except Exception as e:
            logger.error(f"Error during migration verification: {e}")
            return verification_results
    
    def perform_migration(self) -> Dict[str, Any]:
        """Perform complete migration from file-based storage to SQLite.
        
        Returns:
            Dictionary with migration results
        """
        migration_results = {
            'migration_performed': False,
            'urls_migrated': 0,
            'csv_files_migrated': 0,
            'errors': [],
            'verification_passed': False
        }
        
        try:
            # Detect existing data
            data_info = self.detect_existing_data()
            
            if not data_info['migration_needed']:
                logger.info("No existing data found, migration not needed")
                return migration_results
            
            logger.info("Starting migration from file-based storage to SQLite")
            
            # Migrate URLs from JSON
            if data_info['urls_json_exists']:
                logger.info(f"Migrating URLs from {data_info['urls_json_path']}")
                if self.migrate_urls_from_json(data_info['urls_json_path']):
                    migration_results['urls_migrated'] = 1
                else:
                    migration_results['errors'].append("Failed to migrate URLs from JSON")
            
            # Migrate tickers from CSV files
            if data_info['csv_files_exist']:
                logger.info(f"Migrating tickers from {len(data_info['csv_files'])} CSV files")
                for csv_file in data_info['csv_files']:
                    if self.migrate_tickers_from_csv(csv_file):
                        migration_results['csv_files_migrated'] += 1
                    else:
                        migration_results['errors'].append(f"Failed to migrate CSV: {csv_file}")
            
            # Ensure deduplication fields exist
            self.migrate_schema_for_deduplication()
            
            # Verify migration
            if MIGRATION_CONFIG['verify_after_migration']:
                verification_results = self.verify_migration(data_info)
                migration_results['verification_passed'] = verification_results['verification_passed']
            
            migration_results['migration_performed'] = True
            logger.info("Migration completed successfully")
            
            return migration_results
            
        except Exception as e:
            logger.error(f"Error during migration: {e}")
            migration_results['errors'].append(str(e))
            return migration_results
    
    def cleanup_old_files(self, data_info: Dict[str, Any]) -> bool:
        """Clean up old files after successful migration.
        
        Args:
            data_info: Information about original data files
            
        Returns:
            True if cleanup was successful, False otherwise
        """
        if not MIGRATION_CONFIG['remove_old_files_after_migration']:
            logger.info("Skipping cleanup of old files (disabled in config)")
            return True
        
        try:
            cleaned_files = []
            
            # Remove URLs JSON file
            if data_info['urls_json_exists']:
                Path(data_info['urls_json_path']).unlink()
                cleaned_files.append(data_info['urls_json_path'])
            
            # Remove CSV files
            for csv_file in data_info['csv_files']:
                Path(csv_file).unlink()
                cleaned_files.append(csv_file)
            
            logger.info(f"Cleaned up {len(cleaned_files)} old files")
            return True
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return False 