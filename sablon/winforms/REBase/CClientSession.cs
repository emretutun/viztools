using System;
using System.Collections.Generic;
using System.Text;
using System.Net.Sockets;
using System.IO;
using System.ComponentModel;
using System.Diagnostics;
//using System.Timers;
using System.Windows.Forms;

namespace __NS__
{
    public delegate void OnReceivedClEvent(string msg);
    public delegate void OnConnectedClEvent(CClientSession handle);
    public delegate void OnDisconnectedClEvent();


    public class CClientSession 
    {
        Main MainForm = null;
        TcpClient tcpClnt;
        byte[] buffer = new byte[30000];
        NetworkStream stream;

        public OnConnectedClEvent OnConnected = null;
        public OnDisconnectedClEvent OnDisconnected = null;
        public OnReceivedClEvent OnReceived = null;

        Timer ReConnecter = new Timer();

        //public int ID { get; set; }




        public bool currentConnectionState
        {
            get
            {
                if (tcpClnt == null) return false;
                if (tcpClnt.Client == null) return false;
                return tcpClnt.Connected;
            }
        }

        bool lastConnectionState = false;
        public bool isConnected { 
            get
            {
                bool _currentConnectionState = currentConnectionState;

                if (!_currentConnectionState && lastConnectionState) // yeni kopmuş
                    Disconnect();

                lastConnectionState = _currentConnectionState;
                return _currentConnectionState;
            } 
        }




        public string IP { set; get; } = "";
        public int Port { set; get; } = 0;
        public string ParentName { set; get; } = "";

        private string pool = "";


        //int randomClientID = -1;
        public CClientSession()
        {
            RegisterInternalEvents();

            //Random random = new Random();
            //randomClientID = random.Next(100, 999);

            //ReConnecter.Elapsed += new ElapsedEventHandler(ReConnectMediator);
            //ReConnecter.Interval = 3000;
        }


        public void SetParent(Main _mainform)
        {
            MainForm = _mainform;
        }

        private void RegisterInternalEvents()
        {
            OnReceived += new OnReceivedClEvent(OnReceiveMsg);
            OnConnected += new OnConnectedClEvent(OnConnect);
            OnDisconnected += new OnDisconnectedClEvent(OnDisconnect);
        }

        void OnReceiveMsg(string msg) { }
        void OnConnect(object Client) { }
        void OnDisconnect()
        {
            ReConnecter.Enabled = true;
        }

        /*
        public bool Connect(string _ip, int _port)
        {
            IP = _ip;
            Port = _port;
            return Connect();
        }
        */
        public bool Connect()
        {
            ReConnecter.Enabled = true;
            IAsyncResult tcpresult = null;
            try
            {
                tcpClnt = new TcpClient();
                //tcpClnt.SendTimeout = 1;
                //tcpClnt.ReceiveTimeout = 1;
                tcpresult = tcpClnt.BeginConnect(IP, Port, new AsyncCallback(ConnectionCallBack), tcpClnt);
                var success = tcpresult.AsyncWaitHandle.WaitOne(TimeSpan.FromSeconds(1));

                ShowEndpointOnDiagnostic(success);

                if (!success)
                    throw new Exception("Bağlanılamadı. (1sn)");
            }
            catch (Exception e)
            {
                //tcpClnt.EndConnect(tcpresult);
                Console.WriteLine(e.ToString());
                MainForm.Log.Error("CClientSession-Connect", e.ToString());
                return false;
            }
            return true;
        }

        public bool Disconnect()
        {
            try
            {
                tcpClnt.Close();
                OnDisconnected();
            }
            catch (Exception e)
            {
                //tcpClnt.EndConnect(tcpresult);
                Console.WriteLine(e.ToString());
                MainForm.Log.Error("CClientSession-Disconnect", e.ToString());
                return false;
            }
            return true;
        }


        
        /*
        private void ReConnectMediator(object source, ElapsedEventArgs e)
        {
            if (isConnected)
            {
                ReConnecter.Enabled = false;
                return;
            }

            Debug.WriteLine("reconnecting... IP:" + IP + " port:"+ Port.ToString());
            Connect();
        }

        */


        public void ShowEndpointOnDiagnostic(bool state)
        {
            if (MainForm.tbx_diagnostic.Visible)
            {
                string localEndPoint = ((System.Net.IPEndPoint)tcpClnt.Client.LocalEndPoint).Port.ToString();
                string remoteEndPoint = ((System.Net.IPEndPoint)tcpClnt.Client.RemoteEndPoint).ToString();
                string _state = state ? "true" : "false";
                

                MainForm.tbx_diagnostic.AppendText("[TCP]  Parent Name:" + ParentName + "  local port:"+localEndPoint + "    remote IP/port:" + remoteEndPoint + "    connection:" + _state);
                MainForm.tbx_diagnostic.AppendText(Environment.NewLine);
            }
        }

        public bool Send(params object[] prmList)
        {
            lock (this)
            {
                string commandText = ToolsHelper.CreateMessagePack(prmList);  //  burada sadece yan yana getirip endpointer ekliyor
                try
                {
                    Stream stream = tcpClnt.GetStream();
                    //stream.WriteTimeout = (int)TimeSpan.FromSeconds(2000).TotalMilliseconds;
                    //stream.WriteTimeout = 2;
                    byte[] ba = Encoding.GetEncoding("UTF-8").GetBytes(commandText);
                    stream.Write(ba, 0, ba.Length);

                    if (MainForm != null)
                        if (MainForm.SDC.GeneralDelay > 0 && !MainForm.SDC.FasterSend)
                            System.Threading.Thread.Sleep(MainForm.SDC.GeneralDelay);

                        if (MainForm.tbx_diagnostic.Visible)
                        {
                            string localEndPoint = ((System.Net.IPEndPoint)tcpClnt.Client.LocalEndPoint).Port.ToString();
                            string remoteEndPoint = ((System.Net.IPEndPoint)tcpClnt.Client.RemoteEndPoint).ToString();

                            MainForm.tbx_diagnostic.AppendText(localEndPoint + ":" + remoteEndPoint + ":" + commandText.Replace('\n', '▒').Replace('\r', '▓'));
                            MainForm.tbx_diagnostic.AppendText(Environment.NewLine);
                         
                            if (MainForm.cbx_stepMode.Checked)
                                System.Threading.Thread.Sleep((int)MainForm.edt_sleep.Value);

                            if (MainForm.cbx_stepMode_manuel.Checked)
                            {
                                MainForm.btn_DiagnosticStep.Enabled = true;
                                while (!MainForm.diagnosticPasuse)
                                    Application.DoEvents();
                                MainForm.btn_DiagnosticStep.Enabled = false;
                                MainForm.diagnosticPasuse = false;
                            }
                        }

                    //Console.WriteLine(randomClientID.ToString());
                    //Console.WriteLine(((System.Net.IPEndPoint)tcpClnt.Client.LocalEndPoint).Port.ToString());
                    
                    return true;
                }
                catch (Exception ex)
                {
                    Disconnect();
                    Console.WriteLine("CClientSession - Send Error Code: Disconnect");
                    return false;
                }
            }
        }




        private void ConnectionCallBack(IAsyncResult ar)
        {
            //isConnected = tcpClnt.Connected;
            if (isConnected)
            {
                //MessageBox.Show("bağlandı");

                
                stream = tcpClnt.GetStream();
                stream.BeginRead(buffer, 0, buffer.Length, new AsyncCallback(ReceiveCallback), stream);
                
                OnConnected(this);
            }
        }


        private void ReceiveCallback(IAsyncResult ar)
        {

            try
            {
                int iRx = stream.EndRead(ar);
                ReadSocket(Encoding.UTF8.GetString(buffer, 0, iRx - 1));

                stream.Flush();
                stream.BeginRead(buffer, 0, buffer.Length, new AsyncCallback(ReceiveCallback), stream);
            }
            catch
            {
            }
        }



        public void ReadSocket(String aData)  // burada mesajı okuyoruz
        {
            string messageHandle = aData;
            string ErrorCode = aData.Substring(messageHandle.Length, aData.Length - messageHandle.Length);
            OnReceived(messageHandle);
        }

    }
}
