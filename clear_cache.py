import os
import shutil

# Clear cache before committing
if os.path.exists('backend/data/time_series_storage.pkl'):
    os.remove('backend/data/time_series_storage.pkl')

# Function to clear the cache directory

def clear_cache():
    cache_dir = '/Users/fabiosilva/VSCodeProjects/time-series-analyzer/backend/data'
    for filename in os.listdir(cache_dir):
        file_path = os.path.join(cache_dir, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')

if __name__ == '__main__':
    clear_cache()

    cache_dir = "backend/data/"
    for file_name in os.listdir(cache_dir):
        if file_name.endswith(".pkl"):
            file_path = os.path.join(cache_dir, file_name)
            os.remove(file_path)
            print(f"Removed {file_path}")