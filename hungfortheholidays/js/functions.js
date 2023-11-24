/*
	When the bandcamp link is pressed, stop all propagation so AmplitudeJS doesn't
	play the song.
*/
let bandcampLinks = document.getElementsByClassName('bandcamp-link');

for( var i = 0; i < bandcampLinks.length; i++ ){
	bandcampLinks[i].addEventListener('click', function(e){
		e.stopPropagation();
	});
}


let songElements = document.getElementsByClassName('song');

for( var i = 0; i < songElements.length; i++ ){
	/*
		Ensure that on mouseover, CSS styles don't get messed up for active songs.
	*/
	songElements[i].addEventListener('mouseover', function(){
		this.style.backgroundColor = '#00A0FF';

		this.querySelectorAll('.song-meta-data .song-title')[0].style.color = '#FFFFFF';
		this.querySelectorAll('.song-meta-data .song-artist')[0].style.color = '#FFFFFF';

		if( !this.classList.contains('amplitude-active-song-container') ){
			this.querySelectorAll('.play-button-container')[0].style.display = 'block';
		}

		this.querySelectorAll('img.bandcamp-grey')[0].style.display = 'none';
		this.querySelectorAll('img.bandcamp-white')[0].style.display = 'block';
		this.querySelectorAll('.song-duration')[0].style.color = '#FFFFFF';
	});

	/*
		Ensure that on mouseout, CSS styles don't get messed up for active songs.
	*/
	songElements[i].addEventListener('mouseout', function(){
		this.style.backgroundColor = '#FFFFFF';
		this.querySelectorAll('.song-meta-data .song-title')[0].style.color = '#272726';
		this.querySelectorAll('.song-meta-data .song-artist')[0].style.color = '#607D8B';
		this.querySelectorAll('.play-button-container')[0].style.display = 'none';
		this.querySelectorAll('img.bandcamp-grey')[0].style.display = 'block';
		this.querySelectorAll('img.bandcamp-white')[0].style.display = 'none';
		this.querySelectorAll('.song-duration')[0].style.color = '#607D8B';
	});

	/*
		Show and hide the play button container on the song when the song is clicked.
	*/
	songElements[i].addEventListener('click', function(){
		this.querySelectorAll('.play-button-container')[0].style.display = 'none';
	});
}

/*
	Initializes AmplitudeJS
*/
Amplitude.init({
	continue_next: true,
	callbacks: {
		song_change: function(){
			// alert('here');
		}
	},
	"songs": [
		{
			"name": "All I Want For Christmas Is You",
			"artist": "Hung Truong",
			"album": "Hung For the Holidays",
			"url": "songs/All I Want For Christmas Is You.mp3",
			"cover_art_url": "songs/Hung for the Holidays.jpg"
		},
		{
			"name": "Here Comes Santa Claus",
			"artist": "Hung Truong",
			"album": "Hung For the Holidays",
			"url": "songs/Here Comes Santa Claus.mp3",
			"cover_art_url": "songs/Hung for the Holidays.jpg"
		},
		{
			"name": "Feliz Navidad",
			"artist": "Hung Truong",
			"album": "Hung For the Holidays",
			"url": "songs/Feliz Navidad.mp3",
			"cover_art_url": "songs/Hung for the Holidays.jpg"
		},
		{
			"name": "I'm Dreaming of a White Christmas",
			"artist": "Hung Truong",
			"album": "Hung For the Holidays",
			"url": "songs/I'm Dreaming of a White Christmas.mp3",
			"cover_art_url": "songs/Hung for the Holidays.jpg"
		},
		{
			"name": "Last Christmas",
			"artist": "Hung Truong",
			"album": "Hung For the Holidays",
			"url": "songs/Last Christmas.mp3",
			"cover_art_url": "songs/Hung for the Holidays.jpg"
		},
		{
			"name": "Silver Bells",
			"artist": "Hung Truong",
			"album": "Hung For the Holidays",
			"url": "songs/Silver Bells.mp3",
			"cover_art_url": "songs/Hung for the Holidays.jpg"
		},
		{
			"name": "It's Beginning To Look A Lot Like Christmas",
			"artist": "Hung Truong",
			"album": "Hung For the Holidays",
			"url": "songs/It's Beginning To Look A Lot Like Christmas.mp3",
			"cover_art_url": "songs/Hung for the Holidays.jpg"
		},
		{
			"name": "Santa Baby",
			"artist": "Hung Truong",
			"album": "Hung For the Holidays",
			"url": "songs/Santa Baby.mp3",
			"cover_art_url": "songs/Hung for the Holidays.jpg"
		},
		{
			"name": "Rockin' Around The Christmas Tree",
			"artist": "Hung Truong",
			"album": "Hung For the Holidays",
			"url": "songs/Rockin' Around The Christmas Tree.mp3",
			"cover_art_url": "songs/Hung for the Holidays.jpg"
		},
		{
			"name": "Sleigh Ride",
			"artist": "Hung Truong",
			"album": "Hung For the Holidays",
			"url": "songs/Sleigh Ride.mp3",
			"cover_art_url": "songs/Hung for the Holidays.jpg"
		},
		{
			"name": "Let it Snow",
			"artist": "Hung Truong",
			"album": "Hung For the Holidays",
			"url": "songs/Let it Snow.mp3",
			"cover_art_url": "songs/Hung for the Holidays.jpg"
		},
		{
			"name": "The Christmas Song",
			"artist": "Hung Truong",
			"album": "Hung For the Holidays",
			"url": "songs/The Christmas Song.mp3",
			"cover_art_url": "songs/Hung for the Holidays.jpg"
		},
	]
});