using System;
using System.Drawing;
using System.Linq;
using System.Windows.Forms;
using Timer = System.Windows.Forms.Timer;

namespace __NS__
{
    public delegate void OnConnectedEvent(int id, string name);
    public delegate void OnDisconnectedEvent(int id, string name);
    public delegate void OnReceiveMsgEvent(int id, string name, string msg);
    public class Vizrt
    {
        Main MainForm = null;
        CClientSession Client = new CClientSession();

        public OnConnectedEvent OnConnected = null;
        public OnDisconnectedEvent OnDisconnected = null;
        public OnReceiveMsgEvent OnReceivedMsg = null;

        private Timer tmr_tick_Viz = new Timer();


        public int ID { set; get; } = 0;
        public string Name { set; get; } = "undefined";
        public string FullHost { get { return IP + ":" + Port.ToString(); } }
        public string IP { set; get; } = "";
        public int Port { set; get; } = 6100; //RenderEngineDefaultPort.VIZRT;
        public int Active { set; get; }
        public bool isConnected { get { return Client.isConnected; } }
        public int EngineType { set; get; }
        public bool heartbeat { set; get; }

        // bunlar current sceneleri tutar. O an ne yüklü diye...
        public string CurrentScene_Front { set; get; } = "";
        public string CurrentScene_Middle { set; get; } = "";
        public string CurrentScene_Back { set; get; } = "";



        public static string LAYER_FRONT = "FRONT_LAYER";
        public static string LAYER_MAIN = "FRONT_MAIN";
        public static string LAYER_BACK = "FRONT_BACK";


        public Vizrt()
        {
            ConnectionEvents();
        }

        public Vizrt(int id, string name, Main _mainform)
        {
            MainForm = _mainform;
            Client.SetParent(MainForm);


            ID = id;
            Name = name;
            ConnectionEvents();

            tmr_tick_Viz.Interval = 1000;
            tmr_tick_Viz.Enabled = true;
            tmr_tick_Viz.Tick += new System.EventHandler(this.tmr_tick_VizTick);

            //heartbeat = true;   // bu false olursa, heartbeat mesajları gidip gelmez ama kontrolsüz kopmalar 1sn değil 20sn de farkedilir.
        }

        int TryConnectCounter = 0;
        int[] TryTime = new int[] { 1, 5, 10, 30, 60, 120 };
        public void AutoConnectControl(string ipSet)
        {
            TryConnectCounter++;
            if (TryConnectCounter == 121) TryConnectCounter = 61;
            if (TryTime.Contains(TryConnectCounter))
            {
                Name = "undefined";
                IP = "";
                Port = 6100;
                Connect(ipSet);
            }
        }

        private void tmr_tick_VizTick(object sender, EventArgs e)
        {
            if (!isConnected) return;
            if (!heartbeat) return;

            Send("heartbeat", 0);
            waitcounter++;
            if (waitcounter > 2) Client.Disconnect();
        }


        #region Socket Denetimleri


        void ConnectionEvents()
        {
            // alttan gelen eventı yakalama
            Client.OnConnected += new OnConnectedClEvent(OnConnectBase);
            Client.OnDisconnected += new OnDisconnectedClEvent(OnDisconnectBase);
            Client.OnReceived += new OnReceivedClEvent(OnReceivedBase);

            RegisterInternalEvents();
        }


        void OnConnectBase(object Client)
        {
            TryConnectCounter = 0;
            OnConnected(ID, Name);
        }
        void OnDisconnectBase()
        {
            OnDisconnected(ID, Name);
        }

        int waitcounter = 0;
        void OnReceivedBase(string msg)
        {
            waitcounter = 0;
        }



        #region local event handlers
        private void RegisterInternalEvents()
        {
            OnConnected += new OnConnectedEvent(OnConnect);
            OnDisconnected += new OnDisconnectedEvent(OnDisconnect);
            OnReceivedMsg += new OnReceiveMsgEvent(OnReceiveMsg);
        }

        void OnConnect(int id, string name) { }
        void OnDisconnect(int id, string name) { }
        void OnReceiveMsg(int id, string name, string msg) { }
        #endregion


        public bool Disconnect()
        {
            return Client.Disconnect();
        }

        public bool Connect(string ip)
        {
            if (ip.Contains(","))
            {
                string[] splited = ip.Split(',');
                Name = splited[1];
                return Connect(splited[0]);
            }


            if (ip.Contains(":"))
            {
                string[] splited = ip.Split(':');
                IP = splited[0];
                Port = Int16.Parse(splited[1]);
            }
            else IP = ip;
            return Connect();
        }
        public bool Connect(string ip, int port)
        {
            IP = ip;
            Port = port;
            return Connect();
        }

        public bool Connect()
        {
            if (DenyIP(IP)) return false;

            Client.IP = IP;
            Client.Port = Port;
            Client.ParentName = Name;
            waitcounter = -1;
            return Client.Connect();
        }


        private bool DenyIP(string _ip)
        {
            foreach (string _dip in MainForm.denyList)
            {
                if (_dip.Equals(_ip))
                {
                    MessageBox.Show("Bu IP deny listesinde :" + _ip);
                    return true;
                }
            }
            return false;
        }


        #endregion



        #region Packet Send/Receieve


        public int Send(string command)
        {
            return SendPack(command, -1);
        }
        public int Send(string command, int ProccessCode)
        {
            return SendPack(command, ProccessCode);
        }


        int UniqueResponseCode = 0;

        public int SendPack(string command, int ProccessCode)
        {
            if (!Client.isConnected)
                return -1;

            //if (!Client.isConnected)
            //    if (!Connect()) return -1;

            if (ProccessCode == -1)
            {
                Client.Send("-1 " + command);
                return -1;
            }

            if (!Client.Send((UniqueResponseCode).ToString() + " " + command)) ;
            return UniqueResponseCode++;
        }

        #endregion



        string endPointer = "\0";
        private string ScenePack(string layer, string scene)
        {
            //            return layer + "_SCENE*" + scene;
            return "SCENE*" + scene;
        }
        private string StageAnimPack(string layer, string scene, string animName)
        {
            return ScenePack(layer, scene) + "*STAGE*DIRECTOR*" + animName + " ";
        }
        private string TreePack(string layer, string scene)
        {
            return ScenePack(layer, scene) + "*TREE*";
        }
        private string ControlObjectPack(string layer, string scene)
        {
            return TreePack(layer, scene) + "$object*FUNCTION*ControlObject*";
        }

        /*
        public void DirectionSetReverse()
        {
            Send("DIRECTION SET REVERSE");
        }
        */


        public void Visibility(string objectName, bool _state)
        {
            Visibility(Vizrt.LAYER_MAIN, CurrentScene_Middle, objectName, _state);
        }
        public void VisibilityBL(string sceneName, string objectName, bool _state)
        {
            Visibility(Vizrt.LAYER_BACK, sceneName, objectName, _state);
        }

        public void Visible(string objectName)
        {
            Visibility("MIDDLE_LAYER", CurrentScene_Middle, objectName, true);
        }
        public void Invisible(string objectName)
        {
            Visibility("MIDDLE_LAYER", CurrentScene_Middle, objectName, false);
        }
        public void VisibleFL(string objectName)
        {
            Visibility("FRONT_LAYER", CurrentScene_Front, objectName, true);
        }
        public void InvisibleFL(string objectName)
        {
            Visibility("FRONT_LAYER", CurrentScene_Front, objectName, false);
        }
        public void Visible(string layer, string sceneName, string objectName)
        {
            Visibility(layer, sceneName, objectName, true);
        }
        public void Invisible(string layer, string sceneName, string objectName)
        {
            Visibility(layer, sceneName, objectName, false);
        }
        public void Visibility(string layer, string sceneName, string objectName, bool vsb)
        {
            Send("SCENE*" + sceneName + "*TREE*$" + objectName + "*ACTIVE SET " + ((vsb) ? "1" : "0"));
        }



        public void ToStart()
        {
            Send("MAIN_SCENE*STAGE TO_START");
        }

        public void Play(string scene, string animName)
        {
            Play("MAIN", scene, animName);
        }

        public void Play(string layer, string scene, string animName)
        {
            if (animName.Equals("STAGE"))
                Send(layer + "_SCENE*STAGE START");
            else
                Send(StageAnimPack(layer, scene, animName) + "START");
        }

        public void ReversePlay(string scene, string animName)
        {
            ReversePlay("MAIN", scene, animName);
        }

        public void ReversePlay(string layer, string scene, string animName)
        {
            //Send(StageAnimPack(layer, scene, animName) + "DIRECTION SET REVERSE");
            if (animName == null) return;

            if (animName.Equals("STAGE"))
                Send(layer + "_SCENE*STAGE START REVERSE");
            else
                Send(StageAnimPack(layer, scene, animName) + "START REVERSE");
        }


        public void LoadScene_ToFront(string scene)
        {
            //Send("RENDERER*FRONT_LAYER SET_OBJECT SCENE*" + scene);
            //Send("RENDERER*STAGE SHOW 0");


            //Send("RENDERER*FRONT_LAYER SHOW 0");
            //Send("RENDERER*UPDATE SET 1");
            //Send("SCENE CLOSE SCENE*" + scene);
            //Thread.Sleep(100);
            //FrontLayerCleanup();
            CurrentScene_Front = scene;
            Send("RENDERER*FRONT_LAYER SET_OBJECT SCENE*" + scene);
            Send("FRONT_SCENE*STAGE TO_START");


            /*

                        Send("SCENE CLOSE SCENE*" + scene);
                        Send("RENDERER*UPDATE SET 1");
                        Send("RENDERER*FRONT_LAYER SET_OBJECT SCENE*" + scene);
            */

            //Send("RENDERER SET_OBJECT SCENE*" + scene);
            //Send("RENDERER*STAGE SHOW 0");

            /*
            Send("SCENE CLOSE SCENE*" + scene);
            Send("RENDERER*UPDATE SET 1");
            Send("RENDERER SET_OBJECT SCENE*" + scene);
            **/

        }



        public void FullCleanup()
        {
            MoveStart();
            Cleanup();
            //Thread.Sleep(50);
            StageToStart();
        }

        public void MoveStart()
        {
            if (!CurrentScene_Front.Equals("")) Play(LAYER_FRONT, CurrentScene_Front, "BASA_CEK");
            if (!CurrentScene_Middle.Equals("")) Play(LAYER_MAIN, CurrentScene_Middle, "BASA_CEK");
            if (!CurrentScene_Back.Equals("")) Play(LAYER_BACK, CurrentScene_Back, "BASA_CEK");
            //            Cleanup();
            /*            StageToStart("FRONT_SCENE");
                        StageToStart("MAIN_SCENE");
                        StageToStart("BACK_SCENE");*/
        }


        public void StageToStart()
        {/*
            Play(LAYER_FRONT, CurrentScene_Front, "BASA_CEK");
            Play(LAYER_MAIN, CurrentScene_Middle, "BASA_CEK");
            Play(LAYER_BACK, CurrentScene_Back, "BASA_CEK");
            */
            StageToStart("FRONT_SCENE");
            StageToStart("MAIN_SCENE");
            StageToStart("BACK_SCENE");
        }

        public void StageToStart(string _layer)
        {
            Send(_layer + "*STAGE TO_START");
        }

        public void LoadScene_ToBack(string scene)
        {
            //CurrentScene_Back = scene;
            //Send("RENDERER*BACK_LAYER SET_OBJECT SCENE*" + scene);
            CurrentScene_Back = scene;
            Send("RENDERER*BACK_LAYER SET_OBJECT SCENE*" + scene);

            Send("SCENE_EDITOR GET_OBJECT");
            Send("SCENE_EDITOR*FRONT_LAYER GET_OBJECT_INFO");
            Send("SCENE_EDITOR*FRONT_LAYER GET_ACTIVE");
            Send("SCENE_EDITOR*BACK_LAYER GET_OBJECT_INFO");
            Send("SCENE_EDITOR*BACK_LAYER GET_ACTIVE");
            //Send("SCENE*#29099*CONTROL GET 0 1");
            Send("SCENE_EDITOR GET_OBJECT");
            Send("SCENE_EDITOR*FRONT_LAYER GET_OBJECT_INFO");
            Send("SCENE_EDITOR*FRONT_LAYER GET_ACTIVE");
            Send("SCENE_EDITOR*BACK_LAYER GET_OBJECT_INFO");
            Send("SCENE_EDITOR*BACK_LAYER GET_ACTIVE");




            //Send("BACK_SCENE*STAGE TO_START");
        }


        public void LoadScene_justLoad(string scene)
        {
            CurrentScene_Middle = scene;
            Send("SCENE LOAD " + scene);
        }

        public void SceneSubmitToRenderer(string scene)
        {
            Send("RENDERER SET_OBJECT SCENE*" + scene);
        }

        public void LoadScene(string scene)
        {
            CurrentScene_Middle = scene;
            Send("SCENE LOAD " + scene);
            Send("RENDERER SET_OBJECT SCENE*" + scene);
        }



        public void SceneToStartPosition(string scene)
        {
            //Send("RENDERER*STAGE SHOW 0");
            Send("SCENE CLOSE SCENE*" + scene);
        }


        string blankScene = "/2021_HABERTURK/REJI/blank";
        public void Cleanup()
        {
            /*
            Send("TRIO*WEATHER_ACTIVE GET");
            Send("SCENE NEW");
            Send("EDITOR*6 SET_OBJECT");
            Send("EDITOR*7 SET_OBJECT");
            Send("EDITOR*8 SET_OBJECT");
            Send("EDITOR*9 SET_OBJECT");
            Send("SCENE SET_ICON_EDITOR NONE");
            Send("EDITOR*5 SET_OBJECT");
            Send("TRIO*WEATHER_ACTIVE GET");
            Send("SCENE CLOSE " + LAYER_FRONT);
            Send("SCENE CLOSE " + LAYER_MAIN);
            Send("SCENE CLOSE " + LAYER_BACK);
            Send("IMAGE CLEANUP");
            Send("FONT CLEANUP");
            Send("BASE_FONT CLEANUP");
            Send("SCENE_EDITOR*UPDATE SET 0");
            Send("RENDERER*UPDATE SET 0");
            */

            //LoadScene(blankScene);
            //LoadScene_ToFront(blankScene);
            //LoadScene_ToBack(blankScene);


            Send("SCENE CLEANUP");
            Send("GEOM CLEANUP");
            Send("IMAGE CLEANUP");
            Send("FONT CLEANUP");
            Send("BASE_FONT CLEANUP");


            Send("SCEENE_EDITOR * UPDATE SET 0");
            Send("RENDERER * UPDATE SET 0");


            Send("SCENE_EDITOR* UPDATE SET 0");
            Send("RENDERER* UPDATE SET 0");

            Send("EDITOR*0 SET_OBJECT");
            Send("EDITOR*1 SET_OBJECT");
            Send("EDITOR*2 SET_OBJECT");
            Send("EDITOR*3 SET_OBJECT");
            Send("EDITOR*4 SET_OBJECT");
            Send("EDITOR*5 SET_OBJECT");
            Send("EDITOR*6 SET_OBJECT");
            Send("EDITOR*7 SET_OBJECT");
            Send("EDITOR*8 SET_OBJECT");
            Send("EDITOR*9 SET_OBJECT");
            Send("EDITOR*10 SET_OBJECT");

            FrontLayerCleanup();
            MiddleLayerCleanup();
            BackLayerCleanup();
        }


        public void FrontLayerCleanup()
        {
            //LoadScene_ToFront(blankScene);
            CurrentScene_Front = "";
            //Send("FRONT_SCENE*STAGE TO_START");
            Send("RENDERER*FRONT_LAYER SET_OBJECT");
            //UnloadScene(scene);  // acaba gerekir mi? gerekmezmi?
        }


        public void MiddleLayerCleanup()
        {
            //LoadScene(blankScene);
            CurrentScene_Middle = "";
            //Send("MAIN_SCENE*STAGE TO_START");
            Send("RENDERER*MIDDLE_LAYER SET_OBJECT");
            //UnloadScene(scene);  // acaba gerekir mi? gerekmezmi?
        }

        public void BackLayerCleanup()
        {
            //LoadScene_ToBack(blankScene);
            CurrentScene_Back = "";
            //Send("BACK_SCENE*STAGE TO_START");
            Send("RENDERER*BACK_LAYER SET_OBJECT");
            //Send("BACK_SCENE*STAGE TO_START");
            //UnloadScene(scene);  // acaba gerekir mi? gerekmezmi?
        }

        /*
        public void SceneClose(string scene) //  bunlar işlemiyor
        {
            Send("SCENE CLOSE SCENE*" + scene);
            Send("RENDERER*UPDATE SET 1");
            Send("RENDERER*MAIN_LAYER SET_OBJECT SCENE*" + scene);

            Send("SCENE NEW");
            Send("IMAGE CLEANUP");
            Send("FONT CLEANUP");
            Send("BASE_FONT CLEANUP");

        }
        */

        public void Panic1(string scene)
        {
        }

        public void SetImageClip(string scene, string objectName, string filename)
        {
            SetImageClip("MAIN", scene, objectName, filename);
        }
        public void SetImageClip(string layer, string scene, string objectName, string filename)
        {
            Send(TreePack(layer, scene) + "$" + objectName + "*FUNCTION*imageClip*imageLoadFileName SET " + filename);
        }


        public void SetSoftClip(string scene, string objectName, string filename)
        {
            SetSoftClip("MAIN", scene, objectName, filename);
        }
        public void SetSoftClip(string layer, string scene, string objectName, string filename)
        {
            Send(TreePack(layer, scene) + "$" + objectName + "*FUNCTION*SoftClip*clipFile SET " + filename);
        }

        public void SetControlImage(string layer, string scene, string objectName, string filename)
        {
            Send(TreePack(layer, scene) + "$" + objectName + "*FUNCTION*ControlImage*input SET " + filename);
        }



        public void SetImage(string scene, string objectName, string filename)
        {
            SetImage("MAIN", scene, objectName, filename);
        }
        public void SetImage(string layer, string scene, string objectName, string filename)
        {
            //Send(TreePack("MAIN", scene) + "$" + objectName + "*FUNCTION*imageClip*imageLoadFileName SET " + filename);
            Send(TreePack(layer, scene) + "$" + objectName + "*IMAGE SET " + filename);
        }



        public void SetMaterial(string scene, string objectName, string filename)
        {
            SetMaterial("MAIN", scene, objectName, filename);
        }
        public void SetMaterial(string layer, string scene, string objectName, string _material)
        {
            //Send(TreePack("MAIN", scene) + "$" + objectName + "*FUNCTION*imageClip*imageLoadFileName SET " + filename);
            Send(TreePack(layer, scene) + "$" + objectName + "*MATERIAL SET " + _material);
        }


        private string colorVizFormString(Color _cl)
        {
            double _r = 1.0 / (255.0 / _cl.R);
            double _g = 1.0 / (255.0 / _cl.G);
            double _b = 1.0 / (255.0 / _cl.B);
            return _r.ToString() + " " + _g.ToString() + " " + _b.ToString();
        }

        public void SetMaterialColor(string layer, string scene, string objectName, Color _cl)
        {
            Send(TreePack(layer, scene) + "$" + objectName + "*MATERIAL*COLOR SET " + colorVizFormString(_cl));
        }



        private string VizClValue(int value)
        {
            Double v = value / (double)256;
            return v.ToString();
        }

        private string VizColor(Color color)
        {
            string R = VizClValue(color.R);
            string G = VizClValue(color.G);
            string B = VizClValue(color.B);
            return R + " " + G + " " + B;
        }
        public void ClockStart(int startValue)
        {
            Send("CLOCK0*TIME SET " + startValue.ToString());
            Send("CLOCK0" + " START");
        }
        public void ColorSet(string scene, string objectName, Color color)
        {
            Send("-1 SCENE*" + scene + "*TREE*$" + objectName + "*MATERIAL*COLOR SET " + VizColor(color));
            //   Send("-1 SCENE*" + currentScene + "*TREE*$" + objectName + "*GEOM*TEXT SET " + text);

            //            Send("-1 MATERIAL*#4917*COLOR SET " + VizColor(color));
            //            Send("-1 SCENE*" + currentScene + "*TREE*$" + objectName + "*MATERIAL* SET " + text);
        }

        /*
        public void UnloadScene(string scene)   // incelenecek. şimdilik kullanmıyoruz
        {
            Send("TRIO*WEATHER_ACTIVE GET");
            Send("SCENE NEW");
            Send("DATABASE UNLOCK");

            Send("EDITOR*7 SET_OBJECT");
            Send("EDITOR*8 SET_OBJECT");
            Send("EDITOR*9 SET_OBJECT");

            Send("SCENE SET_ICON_EDITOR NONE");
            Send("EDITOR*5 SET_OBJECT");

            Send("TRIO*WEATHER_ACTIVE GET");

            Send("SCENE CLOSE " + scene);
            Send("SCENE CLOSE SCENE*" + scene);

            Send("IMAGE CLEANUP");
            Send("FONT CLEANUP");
            Send("BASE_FONT CLEANUP");


            Send("SCENE_EDITOR*UPDATE SET 0");
            Send("RENDERER*UPDATE SET 0");

            Send("SCENE LOAD SCENE*" + scene);

            Send("EDITOR*6 SET_OBJECT");

        }
        */


        public void UnloadScene(string _sceneName)
        {
            EditorCleanup();
            CloseScene(_sceneName);
        }


        public void EditorCleanup()
        {
            Send("EDITOR*1 SET_OBJECT");
            Send("EDITOR*2 SET_OBJECT");
            Send("EDITOR*3 SET_OBJECT");
            Send("EDITOR*4 SET_OBJECT");


            Send("EDITOR*5 SET_OBJECT");
            Send("EDITOR*6 SET_OBJECT");
            Send("EDITOR*7 SET_OBJECT");
            Send("EDITOR*8 SET_OBJECT");
            Send("EDITOR*9 SET_OBJECT");
        }


        public void CloseScene(string _sceneName)
        {
            Send("SCENE CLOSE " + _sceneName);
            if (CurrentScene_Front.Equals(_sceneName)) CurrentScene_Front = "";
            if (CurrentScene_Middle.Equals(_sceneName)) CurrentScene_Middle = "";
            if (CurrentScene_Back.Equals(_sceneName)) CurrentScene_Back = "";
        }

        public void CloseSceneAllCurrent()
        {
            Send("SCENE CLOSE " + CurrentScene_Front);
            Send("SCENE CLOSE " + CurrentScene_Middle);
            Send("SCENE CLOSE " + CurrentScene_Back);
            CurrentScene_Front = CurrentScene_Middle = CurrentScene_Back = "";
        }




        public void SetObjectText2(string layer, string scene, string objectNameon, string objectName, string text)  //  doğrudan obje set ise
        {
            Send(TreePack(layer, scene) + "$" + objectNameon + "$" + objectName + "*GEOM*TEXT SET " + text);
        }

        public void SetObjectText(string scene, string objectName, string text)  //  doğrudan obje set ise
        {
            SetObjectText("MAIN", scene, objectName, text);
        }
        public void SetObjectText(string layer, string scene, string objectName, string text)  //  doğrudan obje set ise
        {
            Send(TreePack(layer, scene) + "$" + objectName + "*GEOM*TEXT SET " + text);
        }
        public void SetControlObjectText(string scene, string objectName, string text)  //  control object ile text set etme
        {
            SetControlObjectText("MAIN", scene, objectName, text);
        }
        public void SetControlObjectText(string layer, string scene, string objectName, string text)  //  control object ile text set etme
        {
            Send(ControlObjectPack(layer, scene) + "in SET ON " + objectName + " SET " + text + endPointer);
        }
        public void SetControlChannelText(string scene, string channelsName, string text)  //  control channel ile text set etme
        {
            // Send(ControlObjectPack(scene) + "in SET ON " + objectName + " SET " + text + endPointer);          eklenecek. GOT içinde yapmıştım. oradan hazır alabilirim.
        }

    }
}
