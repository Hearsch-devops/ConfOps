FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy app code
COPY Conference-setup/app.py /app/

# Copy templates
COPY Conference-setup/templates/ /app/templates/

# Copy requirements and install dependencies
COPY Conference-setup/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 5000

# Start Gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]