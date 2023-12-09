@echo off
del E:\SQLBackups\*.* /F /Q
sqlcmd -S SERVIATENEA -E -Q "EXEC sp_BackupDatabases @backupLocation='E:\SQLBackups\', @backupType='F'"