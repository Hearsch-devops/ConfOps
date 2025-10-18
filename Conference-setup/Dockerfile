FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY Conference-setup/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY Conference-setup/ /app/

# Expose port
EXPOSE 5000

# Start Gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
