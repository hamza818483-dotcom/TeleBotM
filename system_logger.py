"""System logger for tracking bot status, errors, and logs"""
import time
import os
import sys
import platform
import socket
import subprocess
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from collections import deque

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

# Bot start time (set when bot starts)
_bot_start_time: Optional[float] = None

# Log buffer for recent errors and important events
_log_buffer: deque = deque(maxlen=100)  # Keep last 100 log entries

# Error tracking
_error_count = 0
_last_error_time: Optional[float] = None


def set_bot_start_time():
    """Set the bot start time (called when bot starts)"""
    global _bot_start_time
    _bot_start_time = time.time()


def get_uptime() -> str:
    """Get bot uptime as formatted string"""
    if _bot_start_time is None:
        return "Not tracked"
    
    uptime_seconds = time.time() - _bot_start_time
    
    days = int(uptime_seconds // 86400)
    hours = int((uptime_seconds % 86400) // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    seconds = int(uptime_seconds % 60)
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m {seconds}s"
    elif hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


def log_event(level: str, message: str, error: Optional[Exception] = None):
    """Log an event to the buffer"""
    global _error_count, _last_error_time
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {
        'timestamp': timestamp,
        'level': level.upper(),
        'message': message,
        'error': str(error) if error else None
    }
    
    _log_buffer.append(log_entry)
    
    if level.upper() in ['ERROR', 'CRITICAL']:
        _error_count += 1
        _last_error_time = time.time()


def get_recent_logs(limit: int = 20, level_filter: Optional[str] = None) -> List[Dict]:
    """Get recent log entries"""
    logs = list(_log_buffer)
    
    if level_filter:
        logs = [log for log in logs if log['level'] == level_filter.upper()]
    
    return logs[-limit:]


def get_error_count() -> int:
    """Get total error count"""
    return _error_count


def get_last_error_time() -> Optional[str]:
    """Get last error time as formatted string"""
    if _last_error_time is None:
        return None
    
    return datetime.fromtimestamp(_last_error_time).strftime("%Y-%m-%d %H:%M:%S")


def get_system_config() -> Dict:
    """Get system configuration information"""
    config = {
        'bot_token_set': bool(os.getenv('BOT_TOKEN')),
        'gemini_api_key_set': bool(os.getenv('GEMINI_API_KEY')),
        'gemini_keys_count': len([k for k in os.getenv('GEMINI_API_KEYS', '').split(',') if k.strip()]) if os.getenv('GEMINI_API_KEYS') else 0,
        'channel_id': os.getenv('CHANNEL_ID', 'Not set'),
        'group_id': os.getenv('GROUP_ID', 'Not set'),
        'quiz_marker': os.getenv('QUIZ_MARKER', 'Not set'),
        'explanation_mode': os.getenv('EXPLANATION_MODE', 'off'),
        'max_concurrent_users': int(os.getenv('MAX_CONCURRENT_USERS', 100)),
        'authorized_users_count': len([u for u in os.getenv('AUTHORIZED_USERS', '').split(',') if u.strip()]) if os.getenv('AUTHORIZED_USERS') else 0,
    }
    return config


def get_system_metrics() -> Dict:
    """Get detailed system metrics using psutil"""
    if not PSUTIL_AVAILABLE:
        return {
            'available': False,
            'error': 'psutil not installed'
        }
    
    try:
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count(logical=True)
        cpu_freq = psutil.cpu_freq()
        cpu_per_core = psutil.cpu_percent(interval=0.1, percpu=True)
        
        # Memory metrics
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        disk_io = psutil.disk_io_counters()
        
        # Network metrics
        network_io = psutil.net_io_counters()
        network_connections = len(psutil.net_connections())
        
        # Load average
        load_avg = get_load_average()
        
        # Temperature (if available)
        temperature = get_temperature()
        
        # Process metrics
        process = psutil.Process()
        process_memory = process.memory_info()
        process_cpu = process.cpu_percent(interval=0.1)
        process_threads = process.num_threads()
        process_open_files = len(process.open_files())
        process_create_time = datetime.fromtimestamp(process.create_time())
        
        # Boot time
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        
        return {
            'available': True,
            'cpu': {
                'percent': cpu_percent,
                'count': cpu_count,
                'freq_current': cpu_freq.current if cpu_freq else None,
                'freq_max': cpu_freq.max if cpu_freq else None,
                'per_core': cpu_per_core
            },
            'memory': {
                'total': memory.total,
                'available': memory.available,
                'used': memory.used,
                'percent': memory.percent,
                'swap_total': swap.total,
                'swap_used': swap.used,
                'swap_percent': swap.percent
            },
            'disk': {
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percent': disk.percent,
                'read_bytes': disk_io.read_bytes if disk_io else 0,
                'write_bytes': disk_io.write_bytes if disk_io else 0,
                'read_count': disk_io.read_count if disk_io else 0,
                'write_count': disk_io.write_count if disk_io else 0
            },
            'network': {
                'bytes_sent': network_io.bytes_sent if network_io else 0,
                'bytes_recv': network_io.bytes_recv if network_io else 0,
                'packets_sent': network_io.packets_sent if network_io else 0,
                'packets_recv': network_io.packets_recv if network_io else 0,
                'connections': network_connections
            },
            'process': {
                'memory_rss': process_memory.rss,
                'memory_vms': process_memory.vms,
                'cpu_percent': process_cpu,
                'threads': process_threads,
                'open_files': process_open_files,
                'create_time': process_create_time
            },
            'system': {
                'boot_time': boot_time,
                'platform': platform.system(),
                'platform_release': platform.release(),
                'platform_version': platform.version(),
                'architecture': platform.machine(),
                'processor': platform.processor(),
                'load_average': load_avg,
                'temperature': temperature
            }
        }
    except Exception as e:
        return {
            'available': False,
            'error': str(e)
        }


def format_bytes(bytes_value: int) -> str:
    """Format bytes to human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def get_network_speed() -> Dict:
    """Get network speed metrics (measures over 1 second)"""
    if not PSUTIL_AVAILABLE:
        return {'available': False}
    
    try:
        # Get initial network stats
        net_io_start = psutil.net_io_counters()
        time.sleep(1)
        net_io_end = psutil.net_io_counters()
        
        if net_io_start and net_io_end:
            bytes_sent_speed = net_io_end.bytes_sent - net_io_start.bytes_sent
            bytes_recv_speed = net_io_end.bytes_recv - net_io_start.bytes_recv
            
            return {
                'available': True,
                'upload_speed': bytes_sent_speed,  # bytes per second
                'download_speed': bytes_recv_speed,  # bytes per second
                'upload_speed_formatted': format_bytes(bytes_sent_speed) + '/s',
                'download_speed_formatted': format_bytes(bytes_recv_speed) + '/s'
            }
    except Exception as e:
        return {
            'available': False,
            'error': str(e)
        }
    
    return {'available': False}


def get_network_ping(host: str = "8.8.8.8", count: int = 3) -> Dict:
    """Get network ping/latency to a host"""
    try:
        if platform.system().lower() == 'windows':
            # Windows ping command
            result = subprocess.run(
                ['ping', '-n', str(count), host],
                capture_output=True,
                text=True,
                timeout=10
            )
        else:
            # Linux/Mac ping command
            result = subprocess.run(
                ['ping', '-c', str(count), host],
                capture_output=True,
                text=True,
                timeout=10
            )
        
        if result.returncode == 0:
            output = result.stdout
            # Extract average ping time
            if platform.system().lower() == 'windows':
                # Windows format: "Average = 15ms"
                import re
                match = re.search(r'Average\s*=\s*(\d+)ms', output)
                if match:
                    avg_ping = float(match.group(1))
                else:
                    # Try to find any ping time
                    matches = re.findall(r'(\d+)ms', output)
                    if matches:
                        avg_ping = sum([float(m) for m in matches]) / len(matches)
                    else:
                        return {'available': False, 'error': 'Could not parse ping output'}
            else:
                # Linux format: "min/avg/max/mdev = 10.123/15.456/20.789/5.123 ms"
                import re
                match = re.search(r'min/avg/max.*?=\s*[\d.]+/([\d.]+)/[\d.]+', output)
                if match:
                    avg_ping = float(match.group(1))
                else:
                    return {'available': False, 'error': 'Could not parse ping output'}
            
            return {
                'available': True,
                'host': host,
                'average_ping': avg_ping,
                'average_ping_formatted': f"{avg_ping:.2f} ms"
            }
        else:
            return {
                'available': False,
                'error': f'Ping failed: {result.stderr[:100]}'
            }
    except subprocess.TimeoutExpired:
        return {
            'available': False,
            'error': 'Ping timeout'
        }
    except Exception as e:
        return {
            'available': False,
            'error': str(e)
        }


def get_network_interfaces() -> List[Dict]:
    """Get detailed network interface information"""
    if not PSUTIL_AVAILABLE:
        return []
    
    try:
        interfaces = []
        net_if_addrs = psutil.net_if_addrs()
        net_if_stats = psutil.net_if_stats()
        
        for interface_name, addresses in net_if_addrs.items():
            interface_info = {
                'name': interface_name,
                'addresses': [],
                'is_up': False,
                'speed': 0
            }
            
            # Get interface stats
            if interface_name in net_if_stats:
                stats = net_if_stats[interface_name]
                interface_info['is_up'] = stats.isup
                interface_info['speed'] = stats.speed  # in Mbps
                interface_info['mtu'] = stats.mtu
            
            # Get addresses
            for addr in addresses:
                addr_info = {
                    'family': str(addr.family),
                    'address': addr.address,
                    'netmask': addr.netmask if addr.netmask else None,
                    'broadcast': addr.broadcast if addr.broadcast else None
                }
                interface_info['addresses'].append(addr_info)
            
            interfaces.append(interface_info)
        
        return interfaces
    except Exception as e:
        return []


def get_load_average() -> Optional[Dict]:
    """Get system load average"""
    if not PSUTIL_AVAILABLE:
        return None
    
    try:
        load_avg = psutil.getloadavg()
        cpu_count = psutil.cpu_count()
        
        return {
            '1min': load_avg[0],
            '5min': load_avg[1],
            '15min': load_avg[2],
            'cpu_count': cpu_count,
            '1min_percent': (load_avg[0] / cpu_count) * 100 if cpu_count > 0 else 0
        }
    except Exception:
        return None


def get_temperature() -> Optional[Dict]:
    """Get system temperature sensors (if available)"""
    if not PSUTIL_AVAILABLE:
        return None
    
    try:
        temps = psutil.sensors_temperatures()
        if not temps:
            return None
        
        result = {}
        for name, entries in temps.items():
            if entries:
                # Get the first sensor reading
                result[name] = {
                    'current': entries[0].current,
                    'high': entries[0].high,
                    'critical': entries[0].critical if hasattr(entries[0], 'critical') else None
                }
        
        return result if result else None
    except Exception:
        return None


def get_disk_io_rates() -> Dict:
    """Get current disk I/O rates (bytes per second)"""
    if not PSUTIL_AVAILABLE:
        return {'available': False}
    
    try:
        disk_io_start = psutil.disk_io_counters()
        time.sleep(1)
        disk_io_end = psutil.disk_io_counters()
        
        if disk_io_start and disk_io_end:
            read_rate = disk_io_end.read_bytes - disk_io_start.read_bytes
            write_rate = disk_io_end.write_bytes - disk_io_start.write_bytes
            read_ops = disk_io_end.read_count - disk_io_start.read_count
            write_ops = disk_io_end.write_count - disk_io_start.write_count
            
            return {
                'available': True,
                'read_rate': read_rate,
                'write_rate': write_rate,
                'read_rate_formatted': format_bytes(read_rate) + '/s',
                'write_rate_formatted': format_bytes(write_rate) + '/s',
                'read_ops': read_ops,
                'write_ops': write_ops,
                'read_ops_formatted': f"{read_ops} ops/s",
                'write_ops_formatted': f"{write_ops} ops/s"
            }
    except Exception as e:
        return {
            'available': False,
            'error': str(e)
        }
    
    return {'available': False}

