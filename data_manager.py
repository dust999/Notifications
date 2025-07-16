import json
import os
import threading
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from utils import load_json, save_json

class DataManager:
    """
    Centralized data manager for managing JSON files
    with caching and automatic synchronization
    """
    
    def __init__(self, config_static: Dict[str, Any]):
        self.config_static = config_static
        self._lock = threading.RLock()  # Reentrant lock for nested calls
        
        # In-memory data cache
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._dirty_flags: Dict[str, bool] = {}
        
        # File paths
        self._file_paths = {
            'reminders': config_static["paths"]["notify_path"],
            'backlog': config_static["paths"]["backlog_path"],
            'completed': config_static["paths"]["completed_path"],
            'config_dynamic': "config_dynamic.json"
        }
        
        # Subscribers for changes
        self._subscribers: Dict[str, List[Callable]] = {
            'reminders': [],
            'backlog': [],
            'completed': [],
            'config_dynamic': []
        }
        
        # Initialize cache
        self._initialize_cache()
    
    def _initialize_cache(self):
        """Initialize cache from files"""
        for key, file_path in self._file_paths.items():
            self._load_from_file(key, file_path)
        
        # Clean up outdated completed entries
        self._cleanup_outdated_completed()
    
    def _load_from_file(self, key: str, file_path: str) -> None:
        """Load data from file into cache"""
        try:
            data = load_json(file_path, [])
            self._cache[key] = data
            self._cache_timestamps[key] = os.path.getmtime(file_path) if os.path.exists(file_path) else 0
            self._dirty_flags[key] = False
        except Exception as e:
            print(f"Error loading {key} from {file_path}: {e}")
            self._cache[key] = []
            self._cache_timestamps[key] = 0
            self._dirty_flags[key] = False
    
    def _save_to_file(self, key: str, file_path: str) -> None:
        """Save data from cache to file"""
        try:
            save_json(file_path, self._cache[key])
            self._cache_timestamps[key] = os.path.getmtime(file_path)
            self._dirty_flags[key] = False
        except Exception as e:
            print(f"Error saving {key} to {file_path}: {e}")
    
    def _notify_subscribers(self, key: str) -> None:
        """Notify subscribers about changes"""
        if key in self._subscribers:
            for callback in self._subscribers[key]:
                try:
                    callback(self._cache[key])
                except Exception as e:
                    print(f"Error in subscriber callback for {key}: {e}")
    
    def get_reminders(self) -> List[Dict[str, Any]]:
        """Get list of reminders"""
        with self._lock:
            return self._cache.get('reminders', []).copy()
    
    def get_backlog(self) -> List[Dict[str, Any]]:
        """Get backlog list"""
        with self._lock:
            return self._cache.get('backlog', []).copy()
    
    def get_completed(self) -> List[Dict[str, Any]]:
        """Get list of completed notifications"""
        with self._lock:
            return self._cache.get('completed', []).copy()
    
    def get_config_dynamic(self) -> Dict[str, Any]:
        """Get dynamic configuration"""
        with self._lock:
            return self._cache.get('config_dynamic', {}).copy()
    
    def update_reminders(self, reminders: List[Dict[str, Any]]) -> None:
        """Update list of reminders"""
        with self._lock:
            self._cache['reminders'] = reminders.copy()
            self._dirty_flags['reminders'] = True
            self._save_to_file('reminders', self._file_paths['reminders'])
            self._notify_subscribers('reminders')
    
    def update_backlog(self, backlog: List[Dict[str, Any]]) -> None:
        """Update backlog list"""
        with self._lock:
            self._cache['backlog'] = backlog.copy()
            self._dirty_flags['backlog'] = True
            self._save_to_file('backlog', self._file_paths['backlog'])
            self._notify_subscribers('backlog')
    
    def update_completed(self, completed: List[Dict[str, Any]]) -> None:
        """Update list of completed notifications"""
        with self._lock:
            self._cache['completed'] = completed.copy()
            self._dirty_flags['completed'] = True
            self._save_to_file('completed', self._file_paths['completed'])
            self._notify_subscribers('completed')
    
    def update_config_dynamic(self, config: Dict[str, Any]) -> None:
        """Update dynamic configuration"""
        with self._lock:
            self._cache['config_dynamic'] = config.copy()
            self._dirty_flags['config_dynamic'] = True
            self._save_to_file('config_dynamic', self._file_paths['config_dynamic'])
            self._notify_subscribers('config_dynamic')
    
    def add_reminder(self, reminder: Dict[str, Any]) -> None:
        """Add new reminder"""
        with self._lock:
            reminders = self._cache.get('reminders', [])
            reminders.append(reminder)
            self._cache['reminders'] = reminders
            self._dirty_flags['reminders'] = True
            self._save_to_file('reminders', self._file_paths['reminders'])
            self._notify_subscribers('reminders')
    
    def update_reminder(self, reminder_id: str, updated_reminder: Dict[str, Any]) -> None:
        """Update an existing reminder"""
        with self._lock:
            reminders = self._cache.get('reminders', [])
            
            # Find and update the reminder
            found = False
            for i, reminder in enumerate(reminders):
                if reminder.get('id') == reminder_id:
                    reminders[i] = updated_reminder
                    found = True
                    break
            
            if not found:
                return
            
            self._cache['reminders'] = reminders
            self._dirty_flags['reminders'] = True
            self._save_to_file('reminders', self._file_paths['reminders'])
            self._notify_subscribers('reminders')
    
    def remove_reminder(self, reminder_id: str) -> None:
        """Remove reminder by ID and clean up related data"""
        with self._lock:
            reminders = self._cache.get('reminders', [])
            
            # Find the reminder to get its text for backlog
            reminder_to_remove = None
            for reminder in reminders:
                if reminder.get('id') == reminder_id:
                    reminder_to_remove = reminder
                    break
            
            # Remove from reminders
            reminders = [r for r in reminders if r.get('id') != reminder_id]
            self._cache['reminders'] = reminders
            self._dirty_flags['reminders'] = True
            self._save_to_file('reminders', self._file_paths['reminders'])
            self._notify_subscribers('reminders')
            
            # Remove completed entries for this reminder
            self.remove_completed_entries_for_reminder(reminder_id)
            
            # Add to backlog if reminder was found
            if reminder_to_remove and reminder_to_remove.get('text'):
                self.add_to_backlog(reminder_to_remove['text'])
    
    def add_to_backlog(self, text: str) -> None:
        """Add text to backlog"""
        if not text.strip():
            return
        
        with self._lock:
            backlog = self._cache.get('backlog', [])
            # Check for duplicates (case-insensitive)
            existing_texts = [item.get("text", "").lower() for item in backlog]
            if text.lower() not in existing_texts:
                backlog.append({"text": text})
                self._cache['backlog'] = backlog
                self._dirty_flags['backlog'] = True
                self._save_to_file('backlog', self._file_paths['backlog'])
                self._notify_subscribers('backlog')
    
    def add_completed_entry(self, reminder_id: str) -> None:
        """Add or update entry for completed reminder (only one per id)"""
        with self._lock:
            completed = self._cache.get('completed', [])
            now = datetime.now()
            # Удаляем все старые записи с этим id
            completed = [c for c in completed if c.get("id") != reminder_id]
            # Добавляем новую запись
            completed.append({
                "id": reminder_id,
                "completed_at": now.isoformat()
            })
            self._cache['completed'] = completed
            self._dirty_flags['completed'] = True
            self._save_to_file('completed', self._file_paths['completed'])
            self._notify_subscribers('completed')

    def remove_completed_entries_for_reminder(self, reminder_id: str) -> None:
        """Remove all completed entries for a specific reminder (when reminder is deleted)"""
        with self._lock:
            completed = self._cache.get('completed', [])
            # Remove all entries for this reminder ID
            completed = [c for c in completed if c.get("id") != reminder_id]
            
            self._cache['completed'] = completed
            self._dirty_flags['completed'] = True
            self._save_to_file('completed', self._file_paths['completed'])
            self._notify_subscribers('completed')

    def remove_completed_entry(self, reminder_id: str) -> None:
        """Remove completed entry for a specific reminder (when reminder is edited)"""
        with self._lock:
            completed = self._cache.get('completed', [])
            # Remove all entries for this reminder ID
            completed = [c for c in completed if c.get("id") != reminder_id]
            
            self._cache['completed'] = completed
            self._dirty_flags['completed'] = True
            self._save_to_file('completed', self._file_paths['completed'])
            self._notify_subscribers('completed')
    
    def subscribe(self, data_type: str, callback: Callable) -> None:
        """Subscribe to data changes"""
        if data_type in self._subscribers:
            self._subscribers[data_type].append(callback)
    
    def unsubscribe(self, data_type: str, callback: Callable) -> None:
        """Unsubscribe from data changes"""
        if data_type in self._subscribers and callback in self._subscribers[data_type]:
            self._subscribers[data_type].remove(callback)
    
    def refresh_data(self, data_type: Optional[str] = None) -> None:
        """Force update data from files"""
        with self._lock:
            if data_type:
                if data_type in self._file_paths:
                    self._load_from_file(data_type, self._file_paths[data_type])
            else:
                # Update all data
                for key, file_path in self._file_paths.items():
                    self._load_from_file(key, file_path)
    
    def get_backlog_suggestions(self, prefix: str = "", limit: int = 5) -> List[str]:
        """Get suggestions from backlog"""
        with self._lock:
            backlog = self._cache.get('backlog', [])
            suggestions = []
            for item in backlog:
                text = item.get("text", "")
                if text and (not prefix or text.lower().startswith(prefix.lower())):
                    suggestions.append(text)
            
            # Return last elements, limited by count
            return suggestions[-limit:] if limit else suggestions
    
    def is_dirty(self, data_type: str) -> bool:
        """Check if there are unsaved changes"""
        return self._dirty_flags.get(data_type, False)
    
    def force_save_all(self) -> None:
        """Force save all changed data"""
        with self._lock:
            for key, file_path in self._file_paths.items():
                if self._dirty_flags.get(key, False):
                    self._save_to_file(key, file_path)
    
    def _cleanup_outdated_completed(self):
        """Remove completed entries for non-existent reminders"""
        reminders = self._cache.get('reminders', [])
        completed = self._cache.get('completed', [])
        
        if not reminders or not completed:
            return
        
        # Get current reminder IDs
        current_ids = {reminder.get("id") for reminder in reminders if reminder.get("id")}
        
        # Filter out outdated entries
        valid_completed = [entry for entry in completed if entry.get("id") in current_ids]
        
        # Update if there were changes
        if len(valid_completed) != len(completed):
            self._cache['completed'] = valid_completed
            self._dirty_flags['completed'] = True
            self._save_to_file('completed', self._file_paths['completed'])
            self._notify_subscribers('completed') 