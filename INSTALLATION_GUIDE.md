# LeadBox Installation and Configuration Guide v1.0

## Table of Contents
1. [System Requirements](#system-requirements)
2. [Application Setup](#application-setup)
3. [Database Configuration](#database-configuration)
4. [Environment Variables](#environment-variables)
5. [Running the Application](#running-the-application)
6. [Database Maintenance](#database-maintenance)
7. [Troubleshooting](#troubleshooting)
8. [Backup Procedures](#backup-procedures)

## System Requirements
- Python 3.8 or higher
- MySQL Server 5.7 or higher
- Redis Server (for session management)
- Git (for version control)

## Application Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd leadbox
```

### 2. Create Virtual Environment
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On Unix/MacOS
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

## Database Configuration

### SQLite Database (User Authentication)
The application uses SQLite for user authentication, which is automatically configured in the development environment.

1. The SQLite database file is created at:
   ```
   instance/users.db
   ```

2. Tables are automatically created on first run

### MySQL Database (Leads Management)

1. Create a new MySQL database:
```sql
CREATE DATABASE leadbox_db;
```

2. Create a MySQL user and grant privileges:
```sql
CREATE USER 'leadbox_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON leadbox_db.* TO 'leadbox_user'@'localhost';
FLUSH PRIVILEGES;
```

## Environment Variables
Create a `.env` file in the project root with the following variables:

```env
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-secret-key-here

# Database URLs
DATABASE_URL=mysql://username:password@localhost:3306/leadbox_db
USERS_DATABASE_URL=sqlite:///instance/users.db
LEADS_DATABASE_URL=mysql://username:password@localhost:3306/leadbox_db

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
```

## Running the Application

### Development Mode
```bash
flask run
```

### Production Mode
```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

## Database Maintenance

### Regular Maintenance Tasks

1. **Database Backup**
   ```bash
   # MySQL Backup
   mysqldump -u username -p leadbox_db > backup_$(date +%Y%m%d).sql
   
   # SQLite Backup
   cp instance/users.db instance/users_backup_$(date +%Y%m%d).db
   ```

2. **Database Optimization**
   ```sql
   -- MySQL Optimization
   OPTIMIZE TABLE lead;
   ANALYZE TABLE lead;
   ```

### Automated Backup Script
Create a file named `backup.sh`:
```bash
#!/bin/bash
BACKUP_DIR="backups"
DATETIME=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# MySQL backup
mysqldump -u username -p leadbox_db > "$BACKUP_DIR/mysql_backup_$DATETIME.sql"

# SQLite backup
cp instance/users.db "$BACKUP_DIR/users_backup_$DATETIME.db"

# Cleanup old backups (keep last 7 days)
find "$BACKUP_DIR" -type f -mtime +7 -exec rm {} \;
```

## Troubleshooting

### Common Issues and Solutions

1. **MySQL Connection Issues**
   - Verify MySQL service is running
   - Check credentials in .env file
   - Ensure database and user exist with proper privileges
   - Verify network connectivity and port accessibility

2. **SQLite Database Issues**
   - Ensure instance directory exists and is writable
   - Check file permissions on users.db
   - Verify SQLite version compatibility

3. **Redis Connection Issues**
   - Verify Redis service is running
   - Check Redis configuration in .env
   - Ensure proper port accessibility

### Database Conflict Resolution

1. **SQLAlchemy Binds Configuration**
   - Verify correct database URLs in config.py
   - Ensure proper model binding using __bind_key__
   - Check for conflicting table names across databases

2. **Migration Conflicts**
   ```bash
   # Reset migrations
   rm -rf migrations/
   flask db init
   flask db migrate
   flask db upgrade
   ```

## Security Considerations

1. **Database Security**
   - Use strong passwords
   - Regularly update user credentials
   - Implement proper backup encryption
   - Restrict database access to necessary IPs

2. **Application Security**
   - Keep dependencies updated
   - Implement proper session management
   - Use HTTPS in production
   - Regular security audits

## Version Control

### Database Schema Version Control
1. Use Flask-Migrate for schema changes
2. Document all migrations
3. Test migrations in development first

### Backup Version Control
1. Implement versioned backups
2. Document schema changes
3. Maintain backup history

## Monitoring and Maintenance

1. **Regular Health Checks**
   - Monitor database connections
   - Check application logs
   - Monitor system resources

2. **Performance Optimization**
   - Regular database indexing
   - Query optimization
   - Cache management

---

This documentation covers version 1.0 of the LeadBox application. For updates and new features, please refer to the changelog and future documentation versions.