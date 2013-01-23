# Basic virtualbox configuration
Exec { path => "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" }

node basenode {
  package{["build-essential", "git-core", "vim", "wget", "graphviz", "unzip"]:
    ensure => installed
  }
}

class xfstools {
  package{['lvm2', 'xfsprogs']:
    ensure => installed
  }
}

class java {
  package {['openjdk-7-jre-headless']:
    ensure => installed 
  }
}

class titan {
  include xfstools
  include java
  
  file {"/etc/init/titan.conf":
    source => "puppet:///modules/titan/titan.conf",
    owner  => root
  }

  file {"/home/vagrant/titan.properties":
    source => "puppet:///modules/titan/titan.properties",
    owner  => vagrant
  }

  file {"/root/titan.properties":
    source => "puppet:///modules/titan/titan.properties",
    owner  => root
  }

  exec {"download-titan":
    cwd => "/tmp",
    command => "wget http://s3.thinkaurelius.com/downloads/titan/titan-0.2.0.zip",
    creates => "/tmp/titan-0.2.0.zip"
  }

  exec {"unpack-titan":
    cwd => "/tmp",
    command => "unzip titan-0.2.0.zip",
    creates => "/tmp/titan-0.2.0",
    require => Package["unzip"]
  }

  exec {"install-titan":
    cwd => "/tmp",
    command => "mv titan-0.2.0 /usr/local/titan",
    creates => "/usr/local/titan"
  }
}

class rexster {
  include titan

  exec {"download-rexster":
    cwd => "/tmp",
    command => "wget http://tinkerpop.com/downloads/rexster/rexster-server-2.2.0.zip",
    creates => "/tmp/rexster-server-2.2.0.zip"
  }

  exec {"unzip-rexster":
    cwd => "/tmp",
    command => "unzip rexster-server-2.2.0.zip",
    creates => "/tmp/rexster-server-2.2.0",
    require => [Package["unzip"], Exec["download-rexster"]]
  }

  exec {"install-rexster":
    cwd => "/tmp",
    command => "rm -rf /usr/local/rexster; mv rexster-server-2.2.0 /usr/local/rexster",
    require => Exec["unzip-rexster"]
  }

  exec {"create-titan-ext":
    cwd => "/usr/local/rexster/ext",
    command => "mkdir titan; cp -R /usr/local/titan/lib/* ./titan",
    require => [Exec["install-rexster"], Exec["install-titan"]]
  }

  file {"/etc/rexster.xml":
    source => "puppet:///modules/rexster/rexster.xml",
    owner  => root,
    require => Exec["create-titan-ext"]
  }
  
  service {"titan":
    ensure => running,
    require => File["/etc/rexster.xml"]
  }
}

node thunderdome inherits basenode {
  include rexster
    
  package {["python-pip", "python-dev", "python-nose"]:
    ensure => installed
  }

  exec {"install-requirements":
    cwd => "/vagrant",
    command => "pip install -r requirements.txt",
    require => [Package["python-pip"], Package["python-dev"]]
  }
}
