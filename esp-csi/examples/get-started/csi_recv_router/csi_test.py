import subprocess
import csv
import time
import threading
import re
import numpy as np
# Define the command to run
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
        csv_writer.writerow(['type', 'role', 'mac', 'rssi', 'rate', 'sig_mode', 'mcs', 'bandwidth', 'smoothing', 
                             'not_sounding', 'aggregation', 'stbc', 'fec_coding', 'sgi', 'noise_floor', 
                             'ampdu_cnt', 'channel', 'secondary_channel', 'local_timestamp', 'ant', 
                             'sig_len', 'rx_state', 'real_time_set', 'real_timestamp', 'len', 'CSI_DATA', 
                             'timestamp'])      
        while True:
            line = output_queue.get()
            if line is None:
                break
            if "CSI_DATA" in line:  # Filter for lines containing "CSI_DATA"
                # Get the current timestamp
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

                # Remove the CSI_DATA prefix and split the rest of the line
                csi_data_line = line.split("CSI_DATA,")[1]
                fields = csi_data_line.split(",")
                
                # Parse relevant fields from the data
                s_count = fields[0]
                mac = fields[1]
                rssi = fields[2]
                rate = fields[3]
                sig_mode = fields[4]
                mcs = fields[5]
                bandwidth = fields[6]
                smoothing = fields[7]
                not_sounding = fields[8]
                aggregation = fields[9]
                stbc = fields[10]
                fec_coding = fields[11]
                sgi = fields[12]
                noise_floor = fields[13]
                ampdu_cnt = fields[14]
                channel = fields[15]
                secondary_channel = fields[16]
                local_timestamp = fields[17]
                ant = fields[18]
                sig_len = fields[19]
                rx_state = fields[20]
                real_time_set = fields[21]
                real_timestamp = fields[22]
                csi_data = fields[23:]
                cleaned_data = [re.sub(r'[^\d-]', '', item) for item in csi_data]
                int_data = list(map(int, cleaned_data))
                formatted_data = np.array(int_data)
                formatted_list = formatted_data.tolist()
                # # CSI data is in the 24th field, enclosed in square brackets
                # csi_data = ",".join(fields[23:]).strip('"[]')
                length = len(csi_data)
                # Write the row to CSV
                csv_writer.writerow(['CSI_Data', 'STA', mac, rssi, rate, sig_mode, mcs, bandwidth, smoothing, 
                                     not_sounding, aggregation, stbc, fec_coding, sgi, noise_floor, ampdu_cnt, 
                                     channel, secondary_channel, local_timestamp, ant, sig_len, rx_state, 
                                     real_time_set, real_timestamp, length, formatted_list, timestamp])
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
duration = 600  # 60 seconds

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

