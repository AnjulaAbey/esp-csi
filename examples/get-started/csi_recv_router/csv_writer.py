import subprocess
import csv
import time
import threading


flash_monitor_cmd = ["idf.py", "-p", "/dev/ttyUSB0", "flash", "monitor"]

# Function to run a command and capture its output
def run_command(cmd):
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    while True:
        output = process.stdout.readline()
        if process.poll() is not None and output == b'':
            break
        if output:
            yield output.decode('utf-8').strip()
    rc = process.poll()
    return rc

# Function to filter and write data to a CSV file
def write_to_csv(output_queue):
    csv_filename = 'esp-csi.csv'
    with open(csv_filename, mode='w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file)
        # Write the header
        csv_writer.writerow(['Timestamp', 'CSI Data'])
        while True:
            line = output_queue.get()
            if line is None:
                break
            if "CSI_DATA" in line:  # Filter for lines containing "CSI_DATA"
                # Get the current timestamp
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                # Extract the CSI data part from the line (modify as needed)
                csi_data = line.split("CSI_DATA")[1].strip()
                # Write the timestamp and CSI data to the CSV file
                csv_writer.writerow([timestamp, csi_data])

# Function to run the command with a timeout
def run_with_timeout(cmd, timeout, output_queue):
    def target():
        for line in run_command(cmd):
            print(line)  # Print to console (optional)
            output_queue.put(line)
    thread = threading.Thread(target=target)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        print("Terminating the process after timeout")
        subprocess.run(["pkill", "-f", "idf.py"])  # Terminate the process
        thread.join()
    output_queue.put(None)  # Signal the end of data

# Set the duration (in seconds) for which to run the command
duration = 60  

# Create a queue to communicate between threads
import queue
output_queue = queue.Queue()

# Start the CSV writing thread
csv_thread = threading.Thread(target=write_to_csv, args=(output_queue,))
csv_thread.start()

# Run the flash monitor command with a timeout
run_with_timeout(flash_monitor_cmd, duration, output_queue)

# Wait for the CSV writing thread to finish
csv_thread.join()
