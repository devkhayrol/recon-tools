import socket
import argparse
import concurrent.futures
import dns.resolver

def get_banner(ip_address, port=80):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)  # Set a timeout for connection attempts
            s.connect((ip_address, port))
            s.send(b"GET / HTTP/1.1\r\nHost: " + ip_address.encode() + b"\r\n\r\n")
            banner = s.recv(1024)  # Adjust the buffer size as needed
            return banner.decode(errors='ignore')
    except socket.error as e:
        return f"Error: {e}"

def get_cname_ip(domain):
    try:
        cname = None
        ips = []
        
        answers = dns.resolver.resolve(domain, 'A')
        ips = [r.address for r in answers]
        
        try:
            cname_answer = dns.resolver.resolve(domain, 'CNAME')
            cname = cname_answer[0].target.to_text()
        except dns.resolver.NoAnswer:
            pass
        
        return cname, ips
    except Exception as e:
        return None, []

def check_domains(filename, num_threads, output_file):
    try:
        with open(filename, 'r') as file, open(output_file, 'w') as output:
            domains = file.readlines()
            domains = [domain.strip() for domain in domains]

            with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
                future_to_domain = {executor.submit(get_cname_ip, domain): domain for domain in domains}
                for future in concurrent.futures.as_completed(future_to_domain):
                    domain = future_to_domain[future]
                    try:
                        cname, ips = future.result()
                        if ips:
                            output.write(f"Domain: {domain}\nCNAME: {cname}\nIP Address(es): {', '.join(ips)}\n")
                            print(f"Domain: {domain}\nCNAME: {cname}\nIP Address(es): {', '.join(ips)}")
                            
                            for ip_address in ips:
                                banner = get_banner(ip_address)
                                if banner:
                                    output.write(f"IP Address: {ip_address}\nBanner:\n{banner}\n{'-' * 50}\n")
                                    print(f"IP Address: {ip_address}\nBanner:\n{banner}\n{'-' * 50}\n")
                    except Exception as e:
                        print(f"Error processing {domain}: {e}")
    except FileNotFoundError:
        print("File not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Retrieve CNAME, IP address, and banners for a list of domains.")
    parser.add_argument("-f", "--file", required=True, help="File containing the list of domains")
    parser.add_argument("-t", "--threads", type=int, default=10, help="Number of threads (default=10)")
    parser.add_argument("-o", "--output", default="output.txt", help="Output file to save results (default: output.txt)")
    args = parser.parse_args()

    check_domains(args.file, args.threads, args.output)
