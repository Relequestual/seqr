#By default, we run these commands as root. If we want a file to be owned by Vagrant,
#we do it on the individual provisioning method.
Exec { path => '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin' }
File { owner => 'root', group => 'root', mode => '644' }
Package { allow_virtual => false }

class stages {
    stage { 'bootstrap':  before => Stage['main'] }
    stage { 'cleanup': require => Stage['main'] }
}

class base {

    include stages
    include epel

    class {'::mongodb::server':
      dbpath => $mongodb_dbpath,
    }

    class { 'tools': stage => 'bootstrap' }
    class { 'python':
      stage => 'bootstrap',
      require => [Class['tools']]}

    class { 'vep': }
    class { 'yum_packages': }

    class { 'pip_packages':
            require => [Class[ 'yum_packages' ],
                        Class[ 'python' ]]}

    class { 'symlink': }
    class { 'postgresql': }
    class { 'xbrowse_settings': }

    class { 'django':
            require => [Class[ 'pip_packages' ],
                        Class[ 'xbrowse_settings' ],
                        Class[ 'symlink' ],
                        Class[ 'yum_packages' ]]}

    class { 'supervisord':
            require => [Class[ 'django' ]]}

    class { 'nginx': serve_local => false,
                require => Class[ 'supervisord' ], }

    class { 'gunicorn':
                require => Class[ 'nginx' ],}

}