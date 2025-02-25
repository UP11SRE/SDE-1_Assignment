import os

# If you’re testing locally, you can set it directly.
DATABASE_URL = os.getenv( "DATABASE_URL", "postgresql://db-2_owner:npg_8QYcTj0yGexN@ep-steep-sun-a1crtyt8-pooler.ap-southeast-1.aws.neon.tech/db-2?sslmode=require")