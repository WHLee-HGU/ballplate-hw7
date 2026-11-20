param(
    [ValidateRange(1, 65535)] [int] $Port = 9877,
    [ValidateRange(1, 1000)] [int] $TimeoutMs = 45
)

$ErrorActionPreference = 'Stop'

Add-Type -TypeDefinition @'
using System;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;

public static class BallPlateUdpRelay
{
    public static void Run(int port, int timeoutMs)
    {
        var encoding = new UTF8Encoding(false);
        using (var input = new StreamReader(Console.OpenStandardInput(), encoding))
        using (var output = new StreamWriter(Console.OpenStandardOutput(), encoding))
        {
            output.AutoFlush = true;
            output.WriteLine("{\"relay\":\"ready\"}");

            UdpClient socket = null;
            try
            {
                string line;
                while ((line = input.ReadLine()) != null)
                {
                    try
                    {
                        if (socket == null)
                        {
                            socket = new UdpClient(AddressFamily.InterNetwork);
                            socket.Client.ReceiveTimeout = timeoutMs;
                            socket.Connect(IPAddress.Loopback, port);
                        }

                        byte[] request = encoding.GetBytes(line);
                        socket.Send(request, request.Length);
                        IPEndPoint peer = null;
                        string reply = encoding.GetString(socket.Receive(ref peer));
                        output.WriteLine(reply.Replace('\r', ' ').Replace('\n', ' '));
                    }
                    catch (SocketException error)
                    {
                        // Discard this endpoint so a late reply cannot satisfy the next request.
                        if (socket != null) socket.Close();
                        socket = null;
                        output.WriteLine("{\"relay_error\":\"" + error.SocketErrorCode + "\"}");
                    }
                }
            }
            finally
            {
                if (socket != null) socket.Close();
            }
        }
    }
}
'@

[BallPlateUdpRelay]::Run($Port, $TimeoutMs)
