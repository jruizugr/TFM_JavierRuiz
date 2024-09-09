# ssh_communication.py

import paramiko
import time
class SSHCommunicator:
    def __init__(self, host='169.254.255.254', username='root', password='changeme'):
        self.host = host
        self.username = username
        self.password = password

    def deploy_configuration(self, number_samples, sampling_frequency):
        """
        Deploy the configuration to the Red Pitaya via SSH.
        This method now accepts number_samples and sampling_frequency from the frontend.
        """
        print(sampling_frequency)
        trigger_mask = 1
        trigger_level = 1
        samples_before_trigger = 0
        total_samples = number_samples
        decimation_factor = int(125e6 / (2*sampling_frequency))  # Calculating the decimation factor based on the given sampling frequency
        
        # Constructing the configuration string
        config = f"Trigger_Mask={trigger_mask}\n"
        config += f"Trigger_Level={trigger_level}\n"
        config += f"Samples_Before_Trigger={samples_before_trigger}\n"
        config += f"Total_Samples={total_samples}\n"
        config += f"Decimation_Factor={decimation_factor}\n"
    
        try:
            # Write the configuration to a local file
            with open('config.txt', 'w') as file:
                file.write(config)
    
            # Establish SSH connection
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(self.host, username=self.username, password=self.password)
    
            # Transfer the config file to the Red Pitaya
            sftp = client.open_sftp()
            sftp.put('config.txt', '/root/config.txt')
            sftp.close()
            compile_command = 'cat adc_recorder_trigger.bit > /dev/xdevcfg'
            stdin, stdout, stderr = client.exec_command(compile_command)
            compile_errors = stderr.read().decode()
            # Compile the C program on the Red Pitaya via SSH
            compile_command = 'gcc -o /root/triggerSOFT /root/adc_triggerSOFTWARE.c'
            stdin, stdout, stderr = client.exec_command(compile_command)
            compile_errors = stderr.read().decode()
    
            client.close()
    
            if compile_errors:
                return f"Compilation errors: {compile_errors}"
            return 'Configuration deployed and program compiled successfully.'
    
        except Exception as e:
            return f"Failed to deploy configuration: {e}"
            

    def run_application(self, number_samples, sampling_frequency):
        """
        Run the application on the Red Pitaya and return the output.
        """
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(self.host, username=self.username, password=self.password)
    
            # Run the application on the Red Pitaya
            print("Starting acquisition...")
            command = 'cd /root && ./triggerSOFT'
            stdin, stdout, stderr = client.exec_command(command)
    
            # Wait for acquisition time
            acquisition_time = number_samples / sampling_frequency
            print(acquisition_time)
            print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
            time.sleep(acquisition_time+1)
            print("este time", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
            client.exec_command(f"sleep {acquisition_time}")
    
            # Send stop signal
            command = "touch /tmp/stop_signal"
            client.exec_command(command)
    
           
            # Clean up the stop signal
            delete_command = "rm /tmp/stop_signal"
            client.exec_command(delete_command)
           
            
            # Capture the output
            output = stdout.read().decode()
            
            error = stderr.read().decode()

            # Close the SSH connection
            client.close()
            # Handle any errors
            
            if error:
                return [], f"Error: {error}"
            # Process the captured data
            #data = self.capture_data(output)
            
            return output, None  # Returning data and None (for no error)
    
        except Exception as e:
            return [], f"SSH Command execution failed: {e}"

    def compute_fft(self, data):
        """
        Compute the FFT from the acquired data.
        """
        import numpy as np
        sampling_rate = 125e6  # Example value; replace with actual sampling rate
        fft_result = np.fft.fft(data)
        freq = np.fft.fftfreq(len(data), d=1/sampling_rate)
        return freq, np.abs(fft_result)
