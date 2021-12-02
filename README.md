# N-HW2
Networking Home Work 2

## Server
How to run server?
Setup the server files in a directory.
Note that empty request is considered as index.html
Change the config.json to your liking, don't remove or change the parameters keys or the value type.

Make sure you have those files in the following tree path:
```
------ webServer.py
------ config.json
------ <WebRoot>
        ----- Resources Directory...
           -- Nested Resource
            .
            .
            .
        -- Resources... 
        ...
        ...
        ...
 ```
  ## Client:
  
  
  You may retrieve the pages and resources thorugh the webbrowser with the combo of <IP>:<PORT> where default is 80.
  You may also retrieve the pages and resources through my client script.
  The client can retrieve the local (my server) resources and using GET requests only.
  
  How to run?
  To view the requested resource with list of required resources you can use the following syntax:
  
 ```python  webClient.py <IP> <PORT> <RESOURCE>```

  To download the requested resource with the required resources that can be downloaded use the following syntax:
  
 ```python webClient.py <IP> <PORT> <RESOURCE> <DIST_ROOT>```
  
  
