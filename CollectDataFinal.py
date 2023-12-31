from time import sleep
import paramiko
import csv
import re

# SSH Credentials
username = "msi4"
password = "msi4"

# List of router IP addresses
router_ips = ["10.95.230.5", "10.95.230.6", "10.96.32.3"]

def get_router_info(ip):
    try:
        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=username, password=password, banner_timeout=200)
        connection = ssh.invoke_shell()

        # Function to send command and retrieve output
        def send_command(command):
            connection.send(command + "\n")
            sleep(3)
            connection.send("\n")
            sleep(3)
            output = ""
            while connection.recv_ready():
                output += connection.recv(65535).decode()
                sleep(1)
            return output

        # Send 'sh version' command and get output
        version_output = send_command("sh version")
        os_version_match = re.search(r"Version ([\w.]+)", version_output)
        os_version = os_version_match.group(1) if os_version_match else "Unknown"

        # Send commands for temperature and combine outputs
        temp_output1 = send_command("show env | include CPU temperature:")
        temp_output2 = send_command("show env | include Temp: CPU")
        combined_temp_output = temp_output1 + temp_output2

        # Extract CPU temperature (numeric part only)
        cpu_temp_match = re.search(r"(\d+) Celsius", combined_temp_output)
        cpu_temp = cpu_temp_match.group(1) if cpu_temp_match else "Unknown"

        # Send 'show environment' command for fans
        env_output = send_command("show environment")

        # Check and extract fan statuses based on different outputs
        fan_statuses = []
        if "RPM: fan" in env_output:
            for i in range(0, 4):
                fan_pattern = r"RPM: fan" + str(i) + r".*?Normal"
                fan_status = "OK" if re.search(fan_pattern, env_output) else "-"
                fan_statuses.append(fan_status)
        else:
            for i in range(1, 5):
                fan_pattern = r"Fan " + str(i) + r".*?OK"
                fan_status = "OK" if re.search(fan_pattern, env_output, re.DOTALL) else "-"
                fan_statuses.append(fan_status)

        # Send command for memory utilization
        memory_output = send_command("sh processes memory sorted | include Processor")
        memory_match = re.search(r"Processor Pool Total:\s*(\d+)\s*Used:\s*\d+\s*Free:\s*(\d+)", memory_output)
        if memory_match:
            total_memory = int(memory_match.group(1))
            free_memory = int(memory_match.group(2))
            available_percentage = (free_memory / total_memory) * 100 if total_memory > 0 else 0
            available_percentage_str = f"{available_percentage:.2f}%"
        else:
            total_memory, free_memory, available_percentage_str = "Unknown", "Unknown", "Unknown"

        return [ip, os_version, cpu_temp] + fan_statuses + [total_memory, free_memory, available_percentage_str]
    except Exception as e:
        return [ip, "Error: " + str(e), "Unknown"] + [""] * 4 + ["Unknown", "Unknown", "Unknown"]
    finally:
        if ssh:
            ssh.close()

# Collect data
data = []
for ip in router_ips:
    router_data = get_router_info(ip)
    data.append(router_data)

# Save to CSV
with open('router_data13.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["IP Address", "OS Version", "Temperature (Threshold 80°)", "Fan 1 Status", "Fan 2 Status", "Fan 3 Status", "Fan 4 Status", "Total Memory", "Free Memory", "Available Memory (%)"])
    writer.writerows(data)


