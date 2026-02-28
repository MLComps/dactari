"""Run the Daktari backend server."""
import uvicorn
from config import HOST, PORT, DEBUG

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=DEBUG
    )
